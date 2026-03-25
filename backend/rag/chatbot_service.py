from __future__ import annotations

import re

from sqlalchemy.orm import Session

from agents.agent_manager import AgentManager
from database.models import Statement, Transaction, User
from rag.prompt_builder import build_chat_prompt
from rag.retriever import FinanceRetriever, RetrievalChunk
from services.stats import build_dashboard_payload
from utils.config import settings
from utils.merchant_rules import CATEGORIES


class ChatbotService:
    def __init__(self) -> None:
        self.retriever = FinanceRetriever()
        self.agent_manager = AgentManager()

    def answer(self, db: Session, current_user: User, query: str, mode: str = "rag") -> dict[str, str]:
        query = query.strip()
        selected_mode = (mode or "rag").strip().lower()
        if selected_mode not in {"rag", "general"}:
            selected_mode = "rag"

        if not query:
            return {"answer": "Please ask a question.", "warning": "", "mode": selected_mode}

        if selected_mode == "general":
            return self._answer_general(query)

        return self._answer_rag(db, current_user, query)

    def _answer_general(self, query: str) -> dict[str, str]:
        if not self.agent_manager.client.enabled:
            return {
                "answer": "General chat needs Agent 3 Groq credentials. Add AGENT_THREE_API_KEY in backend/.env to use normal LLM mode.",
                "warning": "",
                "mode": "general",
            }

        try:
            answer = self.agent_manager.client.chat_completion(
                settings.agent_three_model,
                [
                    {
                        "role": "system",
                        "content": (
                            "You are a helpful AI assistant. "
                            "Answer naturally and clearly. "
                            "This mode is general chat and is not restricted to local finance data."
                        ),
                    },
                    {"role": "user", "content": query},
                ],
                temperature=0.3,
            ).strip()
            return {"answer": answer or "I could not generate a response.", "warning": "", "mode": "general"}
        except RuntimeError as exc:
            warning = "API call limit reached, change the api key." if "api call limit reached" in str(exc).lower() else ""
            return {
                "answer": "General chat could not answer right now.",
                "warning": warning,
                "mode": "general",
            }
        except Exception:
            return {"answer": "General chat could not answer right now.", "warning": "", "mode": "general"}

    def _answer_rag(self, db: Session, current_user: User, query: str) -> dict[str, str]:
        transactions = (
            db.query(Transaction)
            .join(Transaction.statement)
            .filter(Statement.user_id == current_user.id)
            .order_by(Transaction.transaction_date.asc())
            .all()
        )
        if not transactions:
            return {"answer": "I do not have enough financial data yet. Upload a statement first.", "warning": "", "mode": "rag"}

        dashboard = build_dashboard_payload(transactions, insights="", include_transactions=False)
        intent = _detect_intent(query)
        kinds = _preferred_kinds_for_intent(intent)
        retrieved_chunks = self.retriever.retrieve_chunks(current_user.id, query, top_k=10, kinds=kinds)

        if len(retrieved_chunks) < 3:
            retrieved_chunks = self.retriever.retrieve_chunks(current_user.id, query, top_k=10)

        context = _build_retrieval_context(retrieved_chunks)
        if not context:
            return {"answer": _fallback_overview_answer(dashboard), "warning": "", "mode": "rag"}

        if self.agent_manager.client.enabled:
            try:
                prompt = build_chat_prompt(user_query=query, retrieved_context=context)
                answer = self.agent_manager.client.chat_completion(
                    settings.agent_three_model,
                    [
                        {
                            "role": "system",
                            "content": (
                                "You are a personal finance assistant. "
                                "Use the retrieved finance context only. "
                                "Answer with concrete numbers, dates, and merchants when available. "
                                "If the retrieved context is insufficient, say that clearly. "
                                "Respond in plain text only. "
                                "Do not use tables, markdown, bullet points, numbered lists, code blocks, or HTML."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.1,
                ).strip()
                if answer:
                    return {"answer": answer, "warning": "", "mode": "rag"}
            except RuntimeError as exc:
                if "api call limit reached" in str(exc).lower():
                    return {
                        "answer": _build_local_answer(intent, retrieved_chunks, dashboard),
                        "warning": "API call limit reached, change the api key.",
                        "mode": "rag",
                    }
            except Exception:
                pass

        return {"answer": _build_local_answer(intent, retrieved_chunks, dashboard), "warning": "", "mode": "rag"}


def _preferred_kinds_for_intent(intent: str) -> list[str] | None:
    mapping = {
        "overview": ["dashboard_summary", "category_breakdown", "top_merchant", "month_summary"],
        "category": ["category_summary", "category_breakdown", "transaction"],
        "merchant": ["merchant_summary", "transaction", "transaction_window"],
        "transaction": ["transaction", "transaction_window", "merchant_summary"],
        "trend": ["month_summary", "day_summary", "transaction_window", "dashboard_summary"],
    }
    return mapping.get(intent)


def _detect_intent(query: str) -> str:
    lowered = query.lower()
    if any(word in lowered for word in ["monthly", "daily", "trend", "average", "over time"]):
        return "trend"
    if _detect_category(query):
        return "category"
    if _extract_named_phrase(query):
        return "merchant"
    if any(word in lowered for word in ["summary", "overview", "finances", "how am i doing", "saving", "savings"]):
        return "overview"
    return "transaction"


def _detect_category(query: str) -> str | None:
    lowered = query.lower()
    for category in CATEGORIES:
        if category.lower() in lowered:
            return category
    aliases = {
        "food": "Food & Dining",
        "dining": "Food & Dining",
        "shopping": "Shopping & Lifestyle",
        "lifestyle": "Shopping & Lifestyle",
        "transport": "Transportation",
        "transportation": "Transportation",
        "bills": "Utilities & Bills",
        "utilities": "Utilities & Bills",
        "rent": "Housing & Rent",
        "housing": "Housing & Rent",
        "entertainment": "Entertainment & Subscriptions",
        "subscriptions": "Entertainment & Subscriptions",
        "subscription": "Entertainment & Subscriptions",
        "groceries": "Groceries & Essentials",
        "essentials": "Groceries & Essentials",
        "health": "Healthcare",
        "healthcare": "Healthcare",
        "education": "Education",
        "friends": "Friends and Relatives",
        "relatives": "Friends and Relatives",
        "income": "Income",
        "investment": "Financial & Investments",
        "investments": "Financial & Investments",
        "financial": "Financial & Investments",
    }
    for alias, category in aliases.items():
        if alias in lowered:
            return category
    return None


def _extract_named_phrase(query: str) -> str:
    match = re.search(r"(?:spent at|paid to|received from|merchant|transaction(?:s)? with|for)\s+(.+)", query, flags=re.I)
    return match.group(1).strip(" ?.") if match else ""


def _build_retrieval_context(chunks: list[RetrievalChunk]) -> str:
    deduped: list[str] = []
    seen: set[str] = set()
    for chunk in chunks:
        if chunk.text in seen:
            continue
        deduped.append(chunk.text)
        seen.add(chunk.text)
    return "\n".join(deduped[:8])


def _build_local_answer(intent: str, chunks: list[RetrievalChunk], dashboard: dict) -> str:
    if intent == "overview":
        return _fallback_overview_answer(dashboard)

    lines = [chunk.text for chunk in chunks[:5]]
    if not lines:
        return _fallback_overview_answer(dashboard)

    if intent in {"merchant", "category"}:
        return "Here is the most relevant finance context I found:\n" + "\n".join(lines)
    if intent == "trend":
        return "Relevant spending trend context:\n" + "\n".join(lines)
    return "Relevant transaction context:\n" + "\n".join(lines)


def _fallback_overview_answer(dashboard: dict) -> str:
    total = dashboard["summary"]["totalSpending"]
    avg = dashboard["summary"]["averageDailySpend"]
    savings = dashboard["summary"]["savingsEstimate"]
    top_category = max(dashboard["categoryBreakdown"], key=lambda item: item["value"], default=None)
    top_merchant = dashboard["topMerchants"][0] if dashboard["topMerchants"] else None

    lines = [f"Your tracked debit spending is Rs {total:.2f}, with an average daily spend of Rs {avg:.2f}."]
    lines.append(f"Your savings estimate is Rs {savings:.2f}.")
    if top_category:
        lines.append(f"Your biggest spending category is {top_category['name']} at Rs {top_category['value']:.2f}.")
    if top_merchant:
        lines.append(f"Your top merchant by spend is {top_merchant['merchant']} at Rs {top_merchant['amount']:.2f}.")
    return " ".join(lines)
