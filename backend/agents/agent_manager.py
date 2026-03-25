from __future__ import annotations

import json
import logging
from time import perf_counter

from services.groq_client import GroqClient
from utils.config import settings
from utils.merchant_rules import CATEGORIES


logger = logging.getLogger(__name__)


class AgentManager:
    def __init__(self) -> None:
        self.agent1_client = GroqClient(settings.agent_one_api_key, agent_name="agent1")
        self.agent2_client = GroqClient(settings.agent_two_api_key, agent_name="agent2")
        self.agent3_client = GroqClient(settings.agent_three_api_key, agent_name="agent3")
        self.client = self.agent3_client

    def enrich_transactions(self, raw_transactions: list[str]) -> list[dict]:
        if not self.agent1_client.enabled:
            return []
        enriched_rows: list[dict] = []
        for chunk in _chunk(raw_transactions, settings.llm_batch_size):
            prompt = _agent1_prompt(strict=True)
            try:
                parsed = self._run_agent1_json(chunk, prompt)
                enriched_rows.extend(parsed if isinstance(parsed, list) else [])
            except Exception as exc:
                logger.warning("Agent 1 enrichment failed for a chunk: %s", exc)
                enriched_rows.extend([{} for _ in chunk])
        return enriched_rows

    def categorize_batch(self, descriptions: list[str]) -> list[str]:
        if not self.agent2_client.enabled or not descriptions:
            return ["Others / Uncategorized" for _ in descriptions]
        categories: list[str] = []
        for chunk in _chunk(descriptions, max(1, min(settings.llm_batch_size, 20))):
            prompt = (
                "You are classifying Indian bank transaction descriptions. "
                "Use only the transaction description text provided for each row. "
                "Return exactly one category for each row from this list: "
                + ", ".join(CATEGORIES)
                + ".\n"
                "Rules:\n"
                "- Personal-name UPI or transfer entries with no clear merchant should default to Others / Uncategorized.\n"
                "- Use Friends and Relatives only when the description clearly indicates a known personal relationship.\n"
                "- Salary, refund, cashback, interest, dividend, and inward credits should be Income.\n"
                "- SIP, mutual fund, stock, loan, EMI, and credit card bill payments should be Financial & Investments.\n"
                "- Unknown or unclear entries must be Others / Uncategorized.\n"
                "Return strict JSON array of category names in the same order as the input rows."
            )
            try:
                content = self._chat_with_client(
                    self.agent2_client,
                    settings.agent_two_model,
                    [
                        {"role": "system", "content": "You categorize bank transactions with high precision."},
                        {
                            "role": "user",
                            "content": f"{prompt}\nDescriptions:\n"
                            + "\n".join(f"{index + 1}. {description}" for index, description in enumerate(chunk)),
                        },
                    ],
                )
                parsed = json.loads(_extract_json(content))
                if not isinstance(parsed, list):
                    parsed = []
                normalized = [item if item in CATEGORIES else "Others / Uncategorized" for item in parsed]
                if len(normalized) < len(chunk):
                    normalized.extend(["Others / Uncategorized"] * (len(chunk) - len(normalized)))
                categories.extend(normalized[: len(chunk)])
            except Exception as exc:
                logger.warning("Agent 2 categorization failed for a chunk: %s", exc)
                categories.extend(["Others / Uncategorized" for _ in chunk])
        return categories

    def summarize_anomalies(self, transactions: list[dict]) -> str:
        if (
            not self.agent3_client.enabled
            or not transactions
            or not settings.enable_ai_insights
            or len(transactions) > settings.max_ai_insight_statement_size
        ):
            return ""
        try:
            content = self._chat_with_client(
                self.agent3_client,
                settings.agent_three_model,
                [
                    {"role": "system", "content": "You summarize finance insights in 3 short bullet points."},
                    {"role": "user", "content": json.dumps(transactions[: settings.max_insight_transactions])},
                ],
                temperature=0.2,
            )
            return content.strip()
        except Exception as exc:
            logger.warning("Agent 3 insight summary failed: %s", exc)
            return ""

    def _run_agent1_json(self, chunk: list[str], prompt: str) -> list[dict]:
        base_messages = [
            {"role": "system", "content": "You extract structured bank transaction JSON. Return only valid JSON."},
            {"role": "user", "content": f"{prompt}\nRows:\n" + "\n".join(chunk)},
        ]
        content = self._chat_with_client(self.agent1_client, settings.agent_one_model, base_messages, temperature=0.1)
        parsed = _try_parse_json(content)
        if parsed is not None:
            return parsed if isinstance(parsed, list) else []

        logger.warning("Agent 1 returned non-JSON output. Retrying once with stricter prompt.")
        retry_messages = [
            {
                "role": "system",
                "content": (
                    "Return only a JSON array. No markdown, no explanation, no prose, no code fences. "
                    "Each item must contain date, merchant, amount, type, description."
                ),
            },
            {"role": "user", "content": f"{_agent1_prompt(strict=True, retry=True)}\nRows:\n" + "\n".join(chunk)},
        ]
        retry_content = self._chat_with_client(
            self.agent1_client,
            settings.agent_one_model,
            retry_messages,
            temperature=0.0,
        )
        retry_parsed = _try_parse_json(retry_content)
        if retry_parsed is None:
            raise RuntimeError("Agent 1 failed to return valid JSON after retry.")
        return retry_parsed if isinstance(retry_parsed, list) else []

    def _chat_with_client(
        self,
        client: GroqClient,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 1024,
    ) -> str:
        started_at = perf_counter()
        logger.info("Calling %s with model %s", client.agent_name, model)
        try:
            return client.chat_completion(
                model,
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        finally:
            logger.info("%s completed in %.2fms", client.agent_name, (perf_counter() - started_at) * 1000)


def _agent1_prompt(*, strict: bool, retry: bool = False) -> str:
    prompt = (
        "Convert the following bank-statement rows into strict JSON. "
        "Return an array of objects with keys: date, merchant, amount, type, description.\n"
        "Rules:\n"
        "- For UPI rows, merchant should be the counterparty name, not the bank, branch, city, or terminal location.\n"
        "- Ignore trailing place names such as branch or ATM locations.\n"
        "- Keep description as the cleaned human-readable transaction narrative.\n"
        "- Preserve row order.\n"
        "- Use null for missing fields.\n"
    )
    if strict:
        prompt += "- Return JSON only. Do not wrap in markdown fences.\n"
    if retry:
        prompt += "- Any output that is not valid JSON is unacceptable.\n"
    return prompt


def _try_parse_json(content: str) -> list[dict] | list[str] | None:
    try:
        return json.loads(_extract_json(content))
    except json.JSONDecodeError:
        return None


def _extract_json(content: str) -> str:
    content = content.strip()
    if content.startswith("```"):
        lines = content.splitlines()
        if len(lines) >= 3:
            return "\n".join(lines[1:-1]).strip()
    return content


def _chunk(items: list[str], chunk_size: int) -> list[list[str]]:
    return [items[index : index + chunk_size] for index in range(0, len(items), max(1, chunk_size))]
