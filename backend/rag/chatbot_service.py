import json
import re
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from agents.agent_manager import AgentManager
from database.models import User
from utils.config import settings


class ChatbotService:
    def __init__(self) -> None:
        self.agent_manager = AgentManager()
        
    def answer(self, db: Session, current_user: User, query: str, mode: str = "rag", section: str = "transactions") -> dict[str, str]:
        query = query.strip()
        selected_mode = (mode or "rag").strip().lower()
        if selected_mode not in {"rag", "general"}:
            selected_mode = "rag"

        if not query:
            return {"answer": "Please ask a question.", "warning": "", "mode": selected_mode}

        if selected_mode == "general":
            return self._answer_general(query)

        return self._answer_sql_rag(db, current_user, query, section)

    def _answer_general(self, query: str) -> dict[str, str]:
        if not self.agent_manager.client.enabled:
            return {
                "answer": "General chat needs Agent 3 API credentials.",
                "warning": "Add GROQ_API_KEY",
                "mode": "general",
            }

        try:
            answer = self.agent_manager.client.chat_completion(
                settings.agent_three_model,
                [
                    {
                        "role": "system",
                        "content": (
                            "You are a helpful AI personal finance assistant. Answer naturally.\n"
                            "This mode is general chat and NOT restricted to local finance data.\n"
                            "CRITICAL: Keep your answer under 200 to 250 words. Do not use markdown tables or complex formatting. "
                            "Give preference to answers in clear bullet points instead of long paragraphs."
                        ),
                    },
                    {"role": "user", "content": query},
                ],
                temperature=0.3,
            ).strip()
            return {"answer": answer or "I could not generate a response.", "warning": "", "mode": "general"}
        except Exception as exc:
            print(f"API Error in Agent 3 (General Chat): {exc}")
            import logging
            logging.getLogger(__name__).error("Agent 3 general chat failed: %s", exc)
            warning = self._warning_from_agent_error(exc)
            return {"answer": "General chat could not answer right now.", "warning": warning, "mode": "general"}

    def _answer_sql_rag(self, db: Session, current_user: User, query: str, section: str) -> dict[str, str]:
        if not self.agent_manager.client.enabled:
            return {
                "answer": "RAG chat needs Agent 3 API credentials.",
                "warning": "Add GROQ_API_KEY",
                "mode": "rag",
            }
            
        try:
            # Step 1: Generate SQL Query Based on Schema
            if section == "loans_and_liabilities":
                schema_context = """
Table: loans
Columns: id (INTEGER), user_id (INTEGER), loan_name (VARCHAR), lender (VARCHAR), principal_amount (FLOAT), interest_rate (FLOAT), tenure_months (INTEGER), emi_amount (FLOAT), start_date (DATE), total_paid (FLOAT), status (VARCHAR)

Table: assets
Columns: id (INTEGER), user_id (INTEGER), asset_name (VARCHAR), purchase_price (FLOAT), purchase_year (INTEGER), rate_per_year (FLOAT)
"""
            else:
                schema_context = """
Table: statements
Columns: id (INTEGER), user_id (INTEGER)

Table: transactions
Columns: id (INTEGER), statement_id (INTEGER), transaction_date (DATE), merchant (VARCHAR), amount (FLOAT), transaction_type (VARCHAR), category (VARCHAR), description (TEXT)

Table: non_banking_transactions
Columns: id (INTEGER), user_id (INTEGER), transaction_date (DATE), beneficiary (VARCHAR), amount (FLOAT), transaction_type (VARCHAR), category (VARCHAR), description (TEXT)
"""
            
            base_prompt = f"""
Given the following SQLite3 schemas:
{schema_context}

The current user has user_id = {current_user.id}.
Only return data for this specific user. For the `transactions` table, you MUST join with `statements` on statement_id to filter by `user_id = {current_user.id}`.

Guidelines:
1. ONLY return a single valid SQLite3 query as a string. Do NOT output markdown formatting like ```sql...```
2. CRITICAL TOKEN LIMIT OPTIMIZATION: Prefer AGGREGATION (SUM, COUNT, AVG) instead of returning raw rows. 
3. Use strict SQLite syntax. For example, instead of MONTH() or YEAR(), use STRFTIME('%m', transaction_date) and STRFTIME('%Y', transaction_date).
4. CRITICAL: SQLite is case-sensitive. ALWAYS use `LOWER(column) = LOWER('value')` or `LIKE` when searching strings (e.g. category, merchant).
5. Limit raw row results to 15 rows if returning multiple unaggregated rows (LIMIT 15). Select only the columns needed to answer the question to save token bounds.
        
User asks: "{query}"
"""

            sql_query = self._generate_sql(base_prompt)
            if not sql_query.lower().startswith("select"):
                return {"answer": "I could not understand your query. Please rephrase it.", "warning": "Generated SQL query was not a SELECT.", "mode": "rag"}

            # Execute the query with a 1-retry loop for corrections
            try:
                result = db.execute(text(sql_query))
                rows = result.fetchmany(20) # Programmatic limit
            except SQLAlchemyError as db_err:
                # Retry logic
                error_msg = str(db_err)
                retry_prompt = f"{base_prompt}\n\nThe previous query you generated was:\n{sql_query}\n\nIt failed with this error:\n{error_msg}\n\nPlease fix the query and return ONLY the corrected SQLite3 query without markdown formatting."
                db.rollback()
                sql_query = self._generate_sql(retry_prompt)

                if not sql_query.lower().startswith("select"):
                    return {"answer": "I could not understand your query. Please rephrase it.", "warning": "Generated SQL query was not a SELECT.", "mode": "rag"}
                    
                result = db.execute(text(sql_query))
                rows = result.fetchmany(15)

            # Extract column names mapping
            try:
                columns = result.keys()
                results_json = [{k: v for k, v in zip(columns, row) if v is not None} for row in rows]
            except Exception:
                results_json = [str(r) for r in rows]

            # Step 2: Synthesis Agent
            final_prompt = f"""
You are a concise personal finance assistant.
A user asked: "{query}"

I executed a SQLite3 query on their data and found:
{json.dumps(results_json, default=str, separators=(',', ':'))}

CRITICAL RULES:
1. Answer the user's question clearly based ONLY on this data. Use concrete numbers and dates. Never hallucinate numbers. Format all monetary amounts using 'Rs. ' (e.g. Rs. 500) instead of the dollar sign ($).
2. If the data is empty `[]` or lacks the answer, state explicitly that you do not have that information recorded.
3. DO NOT use markdown tables. Limit bullet points and formatting to save tokens. Keep answers crisp.
4. Output simple, narrative plain text paragraphs. Do not output anything else.
"""
            
            final_answer = self.agent_manager.client.chat_completion(
                settings.agent_three_model,
                [
                    {"role": "system", "content": "You are an analytical financial assistant. ALWAYS output plain text."},
                    {"role": "user", "content": final_prompt},
                ],
                temperature=0.1,
            ).strip()
            
            return {"answer": final_answer, "warning": "", "mode": "rag"}

        except Exception as exc:
            print(f"API Error in Agent 3 (RAG Chat): {exc}")
            import logging
            logging.getLogger(__name__).error("Agent 3 RAG chat failed: %s", exc)
            warning = self._warning_from_agent_error(exc)
            return {
                "answer": "Sorry, I couldn't compute the answer to your question right now.",
                "warning": warning,
                "mode": "rag",
            }
            
    def _generate_sql(self, prompt: str) -> str:
        sql_query = self.agent_manager.client.chat_completion(
            settings.agent_three_model,
            [
                {"role": "system", "content": "You are a pristine text-to-sql assistant outputting purely SQLite SELECT queries."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        ).strip()
        
        match = re.search(r"```(?:sql|sqlite|mysql)?\s*(.*?)\s*```", sql_query, re.IGNORECASE | re.DOTALL)
        if match:
            sql_query = match.group(1).strip()
        else:
            sql_query = sql_query.replace("```sqlite", "").replace("```sql", "").replace("```mysql", "").replace("```", "").strip()
            
        return sql_query

    def _warning_from_agent_error(self, exc: Exception) -> str:
        message = str(exc).strip()
        lowered = message.lower()
        if "organization is restricted" in lowered:
            return "Agent 3 organization is restricted."
        if "authentication failed" in lowered:
            return "Agent 3 authentication failed."
        if "api call limit" in lowered or "quota" in lowered:
            return "API call limit reached, change the api key."
        return message
