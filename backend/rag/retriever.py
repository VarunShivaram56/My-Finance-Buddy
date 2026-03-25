from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import logging

import chromadb
from sqlalchemy.orm import Session

from database.models import NonBankingTransaction, Statement, Transaction
from rag.embeddings import EmbeddingService
from services.stats import build_dashboard_payload
from utils.config import settings


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetrievalChunk:
    id: str
    text: str
    metadata: dict
    distance: float | None = None


class FinanceRetriever:
    def __init__(self) -> None:
        self.client = self._new_client()
        self.embedding_service = EmbeddingService()

    def _new_client(self):
        return chromadb.PersistentClient(path=settings.chroma_dir)

    def _refresh_client(self) -> None:
        self.client = self._new_client()

    def _collection_name(self, user_id: int) -> str:
        return f"finance_rag_user_{user_id}"

    def _get_collection(self, user_id: int):
        return self.client.get_or_create_collection(name=self._collection_name(user_id))

    def rebuild_index(self, db: Session, user_id: int) -> None:
        self.clear(user_id)
        transactions = (
            db.query(Transaction)
            .join(Transaction.statement)
            .filter(Statement.user_id == user_id)
            .order_by(Transaction.transaction_date.asc())
            .all()
        )
        non_banking_transactions = (
            db.query(NonBankingTransaction)
            .filter(NonBankingTransaction.user_id == user_id)
            .order_by(NonBankingTransaction.transaction_date.asc())
            .all()
        )
        if not transactions and not non_banking_transactions:
            return

        chunks = build_finance_chunks(transactions, non_banking_transactions)
        embeddings = self.embedding_service.embed_many([chunk.text for chunk in chunks])
        self._upsert_chunks(user_id, chunks, embeddings)

    def retrieve_chunks(self, user_id: int, query: str, top_k: int = 8, kinds: list[str] | None = None) -> list[RetrievalChunk]:
        try:
            collection = self._get_collection(user_id)
            if collection.count() == 0:
                return []

            query_embedding = self.embedding_service.embed_many([query])[0]
            query_args = {
                "query_embeddings": [query_embedding],
                "n_results": top_k,
            }
            if kinds:
                query_args["where"] = {"kind": {"$in": kinds}}

            results = collection.query(**query_args)
        except Exception as exc:
            logger.warning("RAG retrieval skipped because the collection was unavailable: %s", exc)
            self._refresh_client()
            return []
        documents = results.get("documents", [[]])[0]
        ids = results.get("ids", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0] if results.get("distances") else []

        chunks: list[RetrievalChunk] = []
        for index, document in enumerate(documents):
            chunks.append(
                RetrievalChunk(
                    id=ids[index],
                    text=document,
                    metadata=metadatas[index] or {},
                    distance=distances[index] if index < len(distances) else None,
                )
            )
        return chunks

    def retrieve(self, user_id: int, query: str, top_k: int = 8, kinds: list[str] | None = None) -> list[str]:
        return [chunk.text for chunk in self.retrieve_chunks(user_id, query, top_k=top_k, kinds=kinds)]

    def clear(self, user_id: int) -> None:
        try:
            self.client.delete_collection(name=self._collection_name(user_id))
        except Exception:
            pass
        finally:
            self._refresh_client()

    def _upsert_chunks(self, user_id: int, chunks: list[RetrievalChunk], embeddings: list[list[float]]) -> None:
        try:
            collection = self._get_collection(user_id)
            collection.upsert(
                ids=[chunk.id for chunk in chunks],
                documents=[chunk.text for chunk in chunks],
                embeddings=embeddings,
                metadatas=[chunk.metadata for chunk in chunks],
            )
        except Exception as exc:
            logger.warning("RAG index upsert retry triggered after collection error: %s", exc)
            self._refresh_client()
            collection = self._get_collection(user_id)
            collection.upsert(
                ids=[chunk.id for chunk in chunks],
                documents=[chunk.text for chunk in chunks],
                embeddings=embeddings,
                metadatas=[chunk.metadata for chunk in chunks],
            )


def build_finance_chunks(
    transactions: list[Transaction],
    non_banking_transactions: list[NonBankingTransaction] | None = None,
) -> list[RetrievalChunk]:
    dashboard = build_dashboard_payload(transactions, insights="")
    chunks: list[RetrievalChunk] = []
    non_banking_transactions = non_banking_transactions or []

    chunks.extend(_build_transaction_chunks(transactions))
    chunks.extend(_build_non_banking_transaction_chunks(non_banking_transactions))
    chunks.extend(_build_merchant_summary_chunks(transactions))
    chunks.extend(_build_category_summary_chunks(transactions))
    chunks.extend(_build_month_summary_chunks(dashboard))
    chunks.extend(_build_dashboard_summary_chunks(dashboard))

    return chunks


def _build_non_banking_transaction_chunks(transactions: list[NonBankingTransaction]) -> list[RetrievalChunk]:
    chunks: list[RetrievalChunk] = []
    for transaction in transactions:
        date_text = transaction.transaction_date.isoformat()
        description = (transaction.description or "").strip()
        text = (
            f"Non-Banking Transaction Record | Date: {date_text} | Beneficiary: {transaction.beneficiary} | "
            f"Category: {transaction.category} | Type: {transaction.transaction_type} | Amount: Rs {transaction.amount:.2f} | "
            f"Description: {description or 'N/A'}"
        )
        chunks.append(
            RetrievalChunk(
                id=f"non-banking-transaction-{transaction.id}",
                text=text,
                metadata={
                    "kind": "transaction",
                    "transaction_id": f"non-banking-{transaction.id}",
                    "merchant": transaction.beneficiary.lower(),
                    "category": transaction.category.lower(),
                    "date": date_text,
                    "type": transaction.transaction_type,
                },
            )
        )
    return chunks


def _build_transaction_chunks(transactions: list[Transaction]) -> list[RetrievalChunk]:
    chunks: list[RetrievalChunk] = []

    for transaction in transactions:
        date_text = transaction.transaction_date.isoformat()
        description = (transaction.description or "").strip()
        text = (
            f"Transaction Record | Date: {date_text} | Merchant: {transaction.merchant} | "
            f"Category: {transaction.category} | Type: {transaction.transaction_type} | "
            f"Amount: Rs {transaction.amount:.2f} | Description: {description or 'N/A'}"
        )
        chunks.append(
            RetrievalChunk(
                id=f"transaction-{transaction.id}",
                text=text,
                metadata={
                    "kind": "transaction",
                    "transaction_id": transaction.id,
                    "merchant": transaction.merchant.lower(),
                    "category": transaction.category.lower(),
                    "date": date_text,
                    "type": transaction.transaction_type,
                },
            )
        )

    grouped_by_month: dict[str, list[Transaction]] = defaultdict(list)
    for transaction in transactions:
        grouped_by_month[transaction.transaction_date.isoformat()[:7]].append(transaction)

    for month, month_transactions in grouped_by_month.items():
        snippets = []
        for item in sorted(month_transactions, key=lambda current: current.transaction_date, reverse=True)[:10]:
            snippets.append(
                f"{item.transaction_date.isoformat()} {item.merchant} Rs {item.amount:.2f} {item.transaction_type} {item.category}"
            )
        debit_total = sum(item.amount for item in month_transactions if item.transaction_type == "debit")
        credit_total = sum(item.amount for item in month_transactions if item.transaction_type == "credit")
        text = (
            f"Monthly Transaction Window | Month: {month} | Debit Total: Rs {debit_total:.2f} | "
            f"Credit Total: Rs {credit_total:.2f} | Transactions: {' ; '.join(snippets)}"
        )
        chunks.append(
            RetrievalChunk(
                id=f"month-window-{month}",
                text=text,
                metadata={"kind": "transaction_window", "month": month},
            )
        )

    return chunks


def _build_merchant_summary_chunks(transactions: list[Transaction]) -> list[RetrievalChunk]:
    merchant_transactions: dict[str, list[Transaction]] = defaultdict(list)
    for transaction in transactions:
        merchant_transactions[transaction.merchant].append(transaction)

    chunks: list[RetrievalChunk] = []
    for merchant, items in merchant_transactions.items():
        debit_total = sum(item.amount for item in items if item.transaction_type == "debit")
        credit_total = sum(item.amount for item in items if item.transaction_type == "credit")
        last_seen = max(item.transaction_date for item in items).isoformat()
        categories = sorted({item.category for item in items})
        text = (
            f"Merchant Summary | Merchant: {merchant} | Debit Total: Rs {debit_total:.2f} | "
            f"Credit Total: Rs {credit_total:.2f} | Transaction Count: {len(items)} | "
            f"Categories: {', '.join(categories)} | Last Seen: {last_seen}"
        )
        chunks.append(
            RetrievalChunk(
                id=f"merchant-summary-{_slugify(merchant)}",
                text=text,
                metadata={
                    "kind": "merchant_summary",
                    "merchant": merchant.lower(),
                    "last_seen": last_seen,
                },
            )
        )
    return chunks


def _build_category_summary_chunks(transactions: list[Transaction]) -> list[RetrievalChunk]:
    grouped: dict[str, list[Transaction]] = defaultdict(list)
    for transaction in transactions:
        grouped[transaction.category].append(transaction)

    chunks: list[RetrievalChunk] = []
    for category, items in grouped.items():
        debit_total = sum(item.amount for item in items if item.transaction_type == "debit")
        credit_total = sum(item.amount for item in items if item.transaction_type == "credit")
        merchant_totals: dict[str, float] = defaultdict(float)
        for item in items:
            if item.transaction_type == "debit":
                merchant_totals[item.merchant] += item.amount
        top_merchants = ", ".join(
            merchant
            for merchant, _ in sorted(merchant_totals.items(), key=lambda current: current[1], reverse=True)[:3]
        )
        text = (
            f"Category Summary | Category: {category} | Debit Total: Rs {debit_total:.2f} | "
            f"Credit Total: Rs {credit_total:.2f} | Transaction Count: {len(items)} | "
            f"Top Merchants: {top_merchants or 'N/A'}"
        )
        chunks.append(
            RetrievalChunk(
                id=f"category-summary-{_slugify(category)}",
                text=text,
                metadata={"kind": "category_summary", "category": category.lower()},
            )
        )
    return chunks


def _build_month_summary_chunks(dashboard: dict) -> list[RetrievalChunk]:
    chunks: list[RetrievalChunk] = []
    for item in dashboard["monthlySpending"]:
        chunks.append(
            RetrievalChunk(
                id=f"month-summary-{item['month']}",
                text=f"Monthly Spending Summary | Month: {item['month']} | Debit Spending: Rs {item['amount']:.2f}",
                metadata={"kind": "month_summary", "month": item["month"]},
            )
        )
    for item in dashboard["dailySpending"][-14:]:
        chunks.append(
            RetrievalChunk(
                id=f"day-summary-{item['date']}",
                text=f"Daily Spending Summary | Date: {item['date']} | Debit Spending: Rs {item['amount']:.2f}",
                metadata={"kind": "day_summary", "date": item["date"]},
            )
        )
    return chunks


def _build_dashboard_summary_chunks(dashboard: dict) -> list[RetrievalChunk]:
    chunks = [
        RetrievalChunk(
            id="dashboard-summary",
            text=(
                f"Dashboard Summary | Total Spending: Rs {dashboard['summary']['totalSpending']:.2f} | "
                f"Average Daily Spend: Rs {dashboard['summary']['averageDailySpend']:.2f} | "
                f"Savings Estimate: Rs {dashboard['summary']['savingsEstimate']:.2f} | "
                f"Transaction Count: {dashboard['summary']['transactionsCount']}"
            ),
            metadata={"kind": "dashboard_summary"},
        )
    ]

    for item in dashboard["topMerchants"]:
        chunks.append(
            RetrievalChunk(
                id=f"top-merchant-{_slugify(item['merchant'])}",
                text=f"Top Merchant Summary | Merchant: {item['merchant']} | Debit Spending: Rs {item['amount']:.2f}",
                metadata={"kind": "top_merchant", "merchant": item["merchant"].lower()},
            )
        )

    for item in dashboard["categoryBreakdown"]:
        chunks.append(
            RetrievalChunk(
                id=f"category-breakdown-{_slugify(item['name'])}",
                text=f"Category Breakdown | Category: {item['name']} | Debit Spending: Rs {item['value']:.2f}",
                metadata={"kind": "category_breakdown", "category": item["name"].lower()},
            )
        )

    return chunks


def _slugify(value: str) -> str:
    return "".join(character if character.isalnum() else "-" for character in value.lower()).strip("-") or "unknown"
