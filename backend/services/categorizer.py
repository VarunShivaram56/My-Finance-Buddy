from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from sqlalchemy.orm import Session

from agents.agent_manager import AgentManager, _rule_based_category
from database.models import Statement, Transaction
from services.description_normalizer import build_description_signature, looks_like_personal_transfer, normalize_description_text
from utils.merchant_rules import CATEGORIES


DEFAULT_CATEGORY = "Others / Uncategorized"


@dataclass(frozen=True)
class CategorizationInput:
    merchant: str | None
    description: str
    transaction_type: str | None = None


class TransactionCategorizer:
    def __init__(self) -> None:
        self.agent_manager = AgentManager()

    def categorize(self, db: Session, user_id: int, items: list[CategorizationInput]) -> list[str]:
        if not items:
            return []

        categories: list[str | None] = [None] * len(items)
        existing_map = self._existing_category_map(db, user_id)

        # Track which items still need LLM resolution
        need_llm_indices: list[int] = []
        llm_descriptions: list[str] = []
        llm_merchants: list[str | None] = []
        llm_types: list[str | None] = []

        for index, item in enumerate(items):
            categorization_text = self._categorization_text(item)
            signature = build_description_signature(categorization_text)

            # ── Step 1: Reuse historical category for this user ───────────
            if signature and signature in existing_map:
                categories[index] = existing_map[signature]
                continue

            # ── Step 2: Personal transfer heuristic ───────────────────────
            if looks_like_personal_transfer(categorization_text):
                categories[index] = DEFAULT_CATEGORY
                continue

            # ── Step 3: Rule-based (merchant map + keyword groups) ────────
            rule_cat = _rule_based_category(
                item.merchant or "",
                item.description or "",
                item.transaction_type,
            )
            if rule_cat:
                categories[index] = rule_cat
                continue

            # ── Step 4: Queue for Agent 2 (LLM) ──────────────────────────
            need_llm_indices.append(index)
            llm_descriptions.append(categorization_text)
            llm_merchants.append(item.merchant)
            llm_types.append(item.transaction_type)

        # Batch-resolve via Agent 2 for genuinely ambiguous items only
        if need_llm_indices:
            llm_results = self.agent_manager.categorize_batch(
                llm_descriptions,
                merchants=llm_merchants,
                transaction_types=llm_types,
            )
            for pos, original_index in enumerate(need_llm_indices):
                cat = llm_results[pos] if pos < len(llm_results) else DEFAULT_CATEGORY
                categories[original_index] = cat if cat in CATEGORIES else DEFAULT_CATEGORY

        return [category or DEFAULT_CATEGORY for category in categories]

    def _categorization_text(self, item: CategorizationInput) -> str:
        merchant = (item.merchant or "").strip()
        description = (item.description or "").strip()
        if merchant and description:
            return f"merchant: {merchant} | description: {description}"
        return merchant or description

    def _existing_category_map(self, db: Session, user_id: int) -> dict[str, str]:
        rows = (
            db.query(Transaction.description, Transaction.category)
            .join(Transaction.statement)
            .filter(Statement.user_id == user_id, Transaction.category.isnot(None))
            .all()
        )
        grouped: dict[str, list[str]] = {}

        for description, category in rows:
            if not description or not category or category == DEFAULT_CATEGORY:
                continue
            signature = build_description_signature(description)
            if not signature:
                continue
            grouped.setdefault(signature, []).append(category)

        return {
            signature: Counter(values).most_common(1)[0][0]
            for signature, values in grouped.items()
        }
