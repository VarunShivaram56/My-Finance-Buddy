from __future__ import annotations

import json
import logging
import time
from typing import TYPE_CHECKING

from services.groq_client import GroqClient
from utils.config import settings
from utils.merchant_rules import CATEGORIES, MERCHANT_CATEGORY_MAP

if TYPE_CHECKING:
    from services.parsing import ParsedTransaction


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Category keyword groups (mirrors categorizer.py — kept here to avoid circular
# imports so Agent 2 can be bypassed without importing the categorizer).
# ---------------------------------------------------------------------------
_CATEGORY_KEYWORD_GROUPS: dict[str, list[str]] = {
    "Housing & Rent": ["rent", "maintenance", "society", "apartment", "property tax", "home loan"],
    "Food & Dining": ["rotti", "pizza", "restaurant", "cafe", "snack", "dining", "food", "bakery", "biryani", "eat"],
    "Groceries & Essentials": ["supermarket", "grocery", "milk", "vegetable", "mart", "essentials", "provision"],
    "Transportation": ["fuel", "petrol", "diesel", "metro", "train", "bus", "auto", "cab", "toll", "parking", "fastag"],
    "Shopping & Lifestyle": ["shopping", "lifestyle", "fashion", "electronics", "shoppers", "store", "mall"],
    "Entertainment & Subscriptions": ["subscription", "movie", "gaming", "music", "premium", "cinema", "theatre"],
    "Utilities & Bills": ["bill", "electric", "water", "internet", "mobile", "broadband", "recharge", "gas", "postpaid", "prepaid"],
    "Healthcare": ["doctor", "medical", "medicine", "pharmacy", "clinic", "hospital", "lab", "diagnostic", "dental", "health"],
    "Education": ["course", "tuition", "fees", "school", "college", "book", "exam", "coaching", "tutorial"],
    "Financial & Investments": ["sip", "mutual", "stock", "demat", "investment", "credit card", "emi", "loan", "nps", "ppf", "fd"],
    "Income": ["salary", "interest", "refund", "cashback", "dividend", "credited by", "inward", "bonus", "commission"],
    "Insurance & Protection": ["insurance", "lic", "premium", "policy", "health cover", "term plan", "endowment"],
    "Travel": ["flight", "airline", "hotel", "booking", "travel", "trip", "tourism", "resort"],
}


def _rule_based_category(merchant: str, description: str, transaction_type: str | None) -> str | None:
    """Fast local lookup — no LLM needed."""
    text = f"{merchant} {description}".lower().strip()
    if not text:
        return None

    # Exact merchant map first (fastest)
    for keyword, category in MERCHANT_CATEGORY_MAP.items():
        if keyword in text:
            return category

    # Credit-type income signals
    if transaction_type == "credit":
        income_keywords = ["salary", "refund", "interest", "cashback", "bonus", "dividend", "inward", "credited"]
        if any(kw in text for kw in income_keywords):
            return "Income"

    # Broader keyword groups
    for category, keywords in _CATEGORY_KEYWORD_GROUPS.items():
        if any(kw in text for kw in keywords):
            return category

    return None


class AgentManager:
    def __init__(self) -> None:
        self.agent1_model = _resolve_groq_model(settings.agent_one_model, agent_name="agent1")
        self.agent2_model = _resolve_groq_model(settings.agent_two_model, agent_name="agent2")
        self.agent3_model = _resolve_groq_model(settings.agent_three_model, agent_name="agent3")
        self.agent1_client = GroqClient(settings.groq_api_key, agent_name="agent1")
        self.agent2_client = GroqClient(settings.groq_api_key, agent_name="agent2")
        self.agent3_client = GroqClient(settings.groq_api_key, agent_name="agent3")
        self.client = self.agent3_client

    # ------------------------------------------------------------------
    # Agent 1 — merchant extraction (confidence-gated, merchant-name only)
    # ------------------------------------------------------------------

    def enrich_low_confidence(
        self,
        raw_transactions: list[str],
        parsed_list: list[ParsedTransaction],
    ) -> list[dict]:
        """
        Run Agent 1 only on rows where the deterministic parser had low
        confidence or failed to extract a merchant. Returns a list of dicts
        (same length as raw_transactions) with a 'merchant' key when found,
        empty dict otherwise.
        """
        result: list[dict] = [{} for _ in raw_transactions]

        if not self.agent1_client.enabled:
            logger.info("Agent 1 disabled (no API key) — skipping merchant enrichment.")
            return result

        threshold = settings.llm_confidence_threshold
        batch_size = max(1, settings.agent1_batch_size)

        # Collect indices that need enrichment
        low_confidence_indices = [
            idx for idx, parsed in enumerate(parsed_list)
            if parsed.confidence < threshold or parsed.merchant is None
        ]

        if not low_confidence_indices:
            logger.info("All transactions parsed with high confidence — Agent 1 skipped entirely.")
            return result

        logger.info(
            "Agent 1: enriching %d/%d low-confidence rows (threshold=%.2f).",
            len(low_confidence_indices),
            len(raw_transactions),
            threshold,
        )

        # Process in small batches
        for batch_start in range(0, len(low_confidence_indices), batch_size):
            batch_indices = low_confidence_indices[batch_start: batch_start + batch_size]
            batch_rows = [raw_transactions[idx] for idx in batch_indices]

            try:
                merchants = self._run_agent1_merchant_extraction(batch_rows)
                for pos, idx in enumerate(batch_indices):
                    merchant = merchants[pos] if pos < len(merchants) else None
                    if merchant:
                        result[idx] = {"merchant": merchant}
            except Exception as exc:
                logger.error("Agent 1 enrichment failed for batch starting at %d: %s", batch_start, exc)
                # Leave result[idx] as empty dict — deterministic value will be kept

            # Respect Groq TPM limits between batches
            if batch_start + batch_size < len(low_confidence_indices):
                time.sleep(settings.agent_inter_batch_sleep)

        return result

    def _run_agent1_merchant_extraction(self, rows: list[str]) -> list[str | None]:
        """
        Call Agent 1 to extract only the merchant/counterparty name from each row.
        Returns a list of merchant name strings (or None) in the same order.
        Small prompt = fewer tokens = no 413, no rate-limit.
        """
        system_msg = (
            "You extract merchant or counterparty names from Indian bank statement rows. "
            "Return ONLY a JSON array of strings, one per row, in the same order. "
            "Use null if merchant cannot be determined. No markdown, no explanation."
        )
        user_msg = _agent1_merchant_prompt(rows)

        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ]

        content = self.agent1_client.chat_completion(
            self.agent1_model,
            messages,
            temperature=0.1,
            max_tokens=512,
        )

        parsed = _try_parse_json(content)
        if parsed is None:
            # Retry once with even stricter instruction
            logger.warning("Agent 1 returned non-JSON. Retrying with strict prompt.")
            messages = [
                {
                    "role": "system",
                    "content": "Return ONLY a valid JSON array of strings/nulls. Zero prose.",
                },
                {"role": "user", "content": user_msg},
            ]
            content = self.agent1_client.chat_completion(
                self.agent1_model, messages, temperature=0.0, max_tokens=512,
            )
            parsed = _try_parse_json(content)

        if not isinstance(parsed, list):
            return [None] * len(rows)

        # Normalise: extract string or None from each element
        merchants: list[str | None] = []
        for item in parsed:
            if isinstance(item, str) and item.strip():
                merchants.append(item.strip()[:255])
            else:
                merchants.append(None)

        # Pad if model returned fewer items than expected
        while len(merchants) < len(rows):
            merchants.append(None)

        return merchants[: len(rows)]

    # ------------------------------------------------------------------
    # Agent 2 — categorisation (rule-first, then LLM for unknowns only)
    # ------------------------------------------------------------------

    def categorize_batch(
        self,
        descriptions: list[str],
        merchants: list[str | None] | None = None,
        transaction_types: list[str | None] | None = None,
    ) -> list[str]:
        """
        Categorise a list of descriptions.
        Order of resolution:
          1. Rule-based (merchant map + keyword groups) — 0 tokens
          2. Historical DB lookup — handled by categorizer.py before this is called
          3. Agent 2 (Groq) — for genuinely ambiguous merchants only
        """
        if not descriptions:
            return []

        merchants = merchants or [None] * len(descriptions)
        transaction_types = transaction_types or [None] * len(descriptions)

        categories: list[str | None] = [None] * len(descriptions)

        # Pass 1: resolve via rule-based lookup (free, instant)
        unresolved_indices: list[int] = []
        for idx, (desc, merchant, txn_type) in enumerate(zip(descriptions, merchants, transaction_types)):
            cat = _rule_based_category(merchant or "", desc, txn_type)
            if cat:
                categories[idx] = cat
            else:
                unresolved_indices.append(idx)

        if not unresolved_indices:
            logger.info("Agent 2: all %d descriptions resolved by rule-based lookup.", len(descriptions))
            return [c or "Others / Uncategorized" for c in categories]

        logger.info(
            "Agent 2: %d of %d descriptions need LLM categorisation.",
            len(unresolved_indices),
            len(descriptions),
        )

        if not self.agent2_client.enabled:
            logger.info("Agent 2 disabled (no API key) — defaulting unresolved to Others / Uncategorized.")
            return [c or "Others / Uncategorized" for c in categories]

        # Deduplicate: group unresolved indices by their text so we only call
        # the LLM once per unique merchant/description pair.
        unique_text_to_indices: dict[str, list[int]] = {}
        for idx in unresolved_indices:
            text_key = f"{(merchants[idx] or '').strip().lower()} | {descriptions[idx].strip().lower()}"
            unique_text_to_indices.setdefault(text_key, []).append(idx)

        unique_texts = list(unique_text_to_indices.keys())
        batch_size = max(1, settings.agent2_batch_size)

        llm_results: list[str] = []
        for batch_start in range(0, len(unique_texts), batch_size):
            batch = unique_texts[batch_start: batch_start + batch_size]
            try:
                batch_categories = self._call_agent2_categorize(batch)
                llm_results.extend(batch_categories)
            except Exception as exc:
                logger.error("Agent 2 categorisation failed for batch at %d: %s", batch_start, exc)
                llm_results.extend(["Others / Uncategorized"] * len(batch))

            if batch_start + batch_size < len(unique_texts):
                time.sleep(settings.agent_inter_batch_sleep)

        # Scatter LLM results back to all original indices
        for text_key, idx_list in unique_text_to_indices.items():
            text_pos = unique_texts.index(text_key)
            cat = llm_results[text_pos] if text_pos < len(llm_results) else "Others / Uncategorized"
            for idx in idx_list:
                categories[idx] = cat

        return [c or "Others / Uncategorized" for c in categories]

    def _call_agent2_categorize(self, texts: list[str]) -> list[str]:
        """Raw LLM call for a single batch of unique texts."""
        categories_str = ", ".join(CATEGORIES)
        system_msg = (
            "You categorise Indian bank transactions into exactly one category per row. "
            f"Valid categories: {categories_str}. "
            "Return ONLY a JSON array of category strings in the same order as input. "
            "No markdown, no explanation, no prose."
        )
        rules = (
            "Rules:\n"
            "- UPI transfers to a personal name with no clear merchant → Others / Uncategorized.\n"
            "- Salary, refund, cashback, interest, dividend, inward credit → Income.\n"
            "- SIP, mutual fund, stock, EMI, loan repayment, credit card bill → Financial & Investments.\n"
            "- Truly unknown entries → Others / Uncategorized.\n"
        )
        numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(texts))
        user_msg = f"{rules}\nTransactions:\n{numbered}"

        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ]

        content = self.agent2_client.chat_completion(
            self.agent2_model,
            messages,
            temperature=0.1,
            max_tokens=256,
        )

        parsed = _try_parse_json(content)
        if not isinstance(parsed, list):
            return ["Others / Uncategorized"] * len(texts)

        normalised = [
            item if item in CATEGORIES else "Others / Uncategorized"
            for item in parsed
        ]
        while len(normalised) < len(texts):
            normalised.append("Others / Uncategorized")
        return normalised[: len(texts)]

    # ------------------------------------------------------------------
    # Agent 3 — AI insights (OpenRouter)
    # ------------------------------------------------------------------

    def summarize_anomalies(self, transactions: list[dict]) -> str:
        if (
            not self.agent3_client.enabled
            or not transactions
            or not settings.enable_ai_insights
            or len(transactions) > settings.max_ai_insight_statement_size
        ):
            return ""
        try:
            content = self.agent3_client.chat_completion(
                self.agent3_model,
                [
                    {"role": "system", "content": "You summarize finance insights in 3 short bullet points."},
                    {"role": "user", "content": json.dumps(transactions[: settings.max_insight_transactions])},
                ],
                temperature=0.2,
            )
            return content.strip()
        except Exception as exc:
            logger.error("Agent 3 insight summary failed: %s", exc)
            return ""

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _chat_with_client(
        self,
        client: GroqClient,
        model: str,
        messages: list[dict],
        temperature: float = 0.1,
        max_tokens: int = 512,
    ) -> str:
        return client.chat_completion(model, messages, temperature=temperature, max_tokens=max_tokens)


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _agent1_merchant_prompt(rows: list[str]) -> str:
    numbered = "\n".join(f"{i + 1}. {row}" for i, row in enumerate(rows))
    return (
        "Extract the merchant or counterparty name from each Indian bank statement row below.\n"
        "Rules:\n"
        "- For UPI rows: the counterparty name comes after UPI/DR/<txn_id>/ or UPI/CR/<txn_id>/ or inside parentheses.\n"
        "- For NEFT/RTGS/IMPS: the beneficiary name after the transfer code.\n"
        "- Ignore bank names, branch names, city names, terminal IDs, reference numbers, UPI IDs.\n"
        "- Return null if no valid merchant/person name can be identified.\n"
        "- Keep names short and clean (max 5 words).\n"
        f"Return a JSON array of {len(rows)} items (strings or null), in order.\n\n"
        f"Rows:\n{numbered}"
    )


def _try_parse_json(content: str) -> list | None:
    try:
        return json.loads(_extract_json(content))
    except (json.JSONDecodeError, TypeError):
        return None


def _extract_json(content: str) -> str:
    content = (content or "").strip()
    # Strip markdown fences
    if content.startswith("```"):
        lines = content.splitlines()
        # Find closing fence
        end = next((i for i in range(len(lines) - 1, 0, -1) if lines[i].strip() == "```"), None)
        if end:
            return "\n".join(lines[1:end]).strip()
    return content


# Models supported on Groq free tier with generous TPM limits.
# groq/compound routes internally to openai/gpt-oss-120b (only 8k TPM — avoid!).
_SUPPORTED_GROQ_MODELS = {
    "llama-3.1-8b-instant",   # 30k TPM — recommended for Agent 1 & 2
    "llama3-8b-8192",         # 30k TPM — fallback
    "llama3-70b-8192",        # 6k TPM — use only if quality is insufficient
    "gemma2-9b-it",           # 15k TPM — alternative
    "groq/compound",          # heavy compound router — NOT recommended (8k TPM sub-limit)
}
_DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"


def _resolve_groq_model(model: str, *, agent_name: str) -> str:
    normalized = (model or "").strip()
    if normalized in _SUPPORTED_GROQ_MODELS:
        return normalized
    logger.warning(
        "%s received unsupported or empty model '%s'. Falling back to %s.",
        agent_name,
        normalized or "<empty>",
        _DEFAULT_GROQ_MODEL,
    )
    return _DEFAULT_GROQ_MODEL
