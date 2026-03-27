from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from sqlalchemy.orm import Session

from agents.agent_manager import AgentManager
from database.models import Statement, Transaction
from services.description_normalizer import build_description_signature, looks_like_personal_transfer, normalize_description_text
from utils.merchant_rules import CATEGORIES, MERCHANT_CATEGORY_MAP


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
        unresolved_by_signature: dict[str, list[int]] = {}
        signature_to_prompt_text: dict[str, str] = {}

        for index, item in enumerate(items):
            categorization_text = self._categorization_text(item)
            signature = build_description_signature(categorization_text)
            signature_to_prompt_text[signature] = categorization_text

            if signature and signature in existing_map:
                categories[index] = existing_map[signature]
                continue

            if looks_like_personal_transfer(categorization_text):
                categories[index] = DEFAULT_CATEGORY
                continue

            category = self._rule_based_category(categorization_text, item.transaction_type)
            if category:
                categories[index] = category
                continue

            unresolved_by_signature.setdefault(signature or f"row-{index}", []).append(index)

        if unresolved_by_signature:
            signatures = list(unresolved_by_signature.keys())
            descriptions = [signature_to_prompt_text.get(signature, "") for signature in signatures]
            llm_categories = self.agent_manager.categorize_batch(descriptions)
            for signature, category in zip(signatures, llm_categories):
                normalized = category if category in CATEGORIES else DEFAULT_CATEGORY
                for index in unresolved_by_signature[signature]:
                    categories[index] = normalized

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

    def _rule_based_category(self, description: str, transaction_type: str | None) -> str | None:
        normalized = normalize_description_text(description)
        if not normalized:
            return None

        for keyword, category in MERCHANT_CATEGORY_MAP.items():
            if keyword in normalized:
                return category

        keyword_groups = {
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
        for category, keywords in keyword_groups.items():
            if any(keyword in normalized for keyword in keywords):
                return category

        if transaction_type == "credit" and any(keyword in normalized for keyword in ["salary", "refund", "interest", "cashback", "bonus"]):
            return "Income"

        return None
