from __future__ import annotations

import hashlib
import logging
from datetime import date

from sqlalchemy.orm import Session

from fastapi import HTTPException

from agents.agent_manager import AgentManager
from database.models import Statement, Transaction, User
from rag.retriever import FinanceRetriever
from services.bank_profiles import get_supported_banks_payload
from services.categorizer import CategorizationInput, TransactionCategorizer
from services.dashboard_cache import dashboard_cache
from services.description_normalizer import build_description_signature
from services.parsing import normalize_transaction_rows, parse_transaction_text
from services.pdf_extractor import extract_bank_rows, extract_rows_from_pdf
from services.stats import build_dashboard_payload, empty_dashboard_payload
from utils.merchant_rules import CATEGORIES
from utils.config import settings


logger = logging.getLogger(__name__)


class StatementService:
    def __init__(self) -> None:
        self.agent_manager = AgentManager()
        self.categorizer = TransactionCategorizer()
        self.retriever = FinanceRetriever()

    def process_statement(self, db: Session, current_user: User, filename: str, file_bytes: bytes, bank_name: str = "karnataka_bank") -> dict:
        source_hash = hashlib.sha256(file_bytes).hexdigest()
        existing_statement = (
            db.query(Statement)
            .filter(Statement.source_hash == source_hash, Statement.user_id == current_user.id)
            .first()
        )
        if existing_statement:
            raise ValueError("This statement appears to have already been uploaded.")

        rows = self._extract_rows(file_bytes, bank_name)
        raw_transactions = normalize_transaction_rows(rows)

        if not raw_transactions:
            raise ValueError(
                "No transaction rows could be extracted from this PDF. Please use a text-based bank statement PDF, not a scanned image."
            )

        parsed = [parse_transaction_text(row) for row in raw_transactions]
        low_confidence_indices = [
            index for index, transaction in enumerate(parsed) if transaction.confidence < settings.llm_confidence_threshold
        ]

        if low_confidence_indices:
            enriched = self.agent_manager.enrich_transactions([raw_transactions[index] for index in low_confidence_indices])
            for index, llm_row in zip(low_confidence_indices, enriched):
                parsed[index].date = llm_row.get("date") or parsed[index].date
                parsed[index].merchant = llm_row.get("merchant") or parsed[index].merchant
                parsed[index].amount = llm_row.get("amount") or parsed[index].amount
                parsed[index].transaction_type = llm_row.get("type") or parsed[index].transaction_type
                parsed[index].description = llm_row.get("description") or parsed[index].description
                parsed[index].confidence = max(parsed[index].confidence, 0.85)

        valid_transactions = [
            transaction
            for transaction in parsed
            if transaction.date and transaction.merchant and transaction.amount is not None and transaction.transaction_type
        ]

        if not valid_transactions:
            raise ValueError(
                "The PDF was uploaded, but no valid transactions could be parsed. The statement layout may need the text-line fallback or OCR."
            )

        categories = self.categorizer.categorize(
            db,
            current_user.id,
            [
                CategorizationInput(
                    merchant=transaction.merchant,
                    description=transaction.description or transaction.raw_text,
                    transaction_type=transaction.transaction_type,
                )
                for transaction in valid_transactions
            ],
        )

        statement = Statement(filename=filename, source_hash=source_hash, user_id=current_user.id)
        db.add(statement)
        db.flush()

        db_transactions: list[Transaction] = []
        for transaction, category in zip(valid_transactions, categories):
            try:
                transaction_date = date.fromisoformat(transaction.date)
            except ValueError:
                continue
            db_transaction = Transaction(
                statement_id=statement.id,
                transaction_date=transaction_date,
                merchant=transaction.merchant or "Unknown",
                amount=transaction.amount or 0,
                transaction_type=transaction.transaction_type or "debit",
                category=category,
                description=transaction.description,
                raw_text=transaction.raw_text,
                parser_confidence=transaction.confidence,
            )
            db.add(db_transaction)
            db_transactions.append(db_transaction)

        if not db_transactions:
            db.rollback()
            raise ValueError("Transactions were detected, but none could be validated for storage.")

        db.commit()
        for transaction in db_transactions:
            db.refresh(transaction)

        insights = self.agent_manager.summarize_anomalies(
            [
                {
                    "date": transaction.transaction_date.isoformat(),
                    "merchant": transaction.merchant,
                    "amount": transaction.amount,
                    "category": transaction.category,
                }
                for transaction in db_transactions
            ]
        )
        all_transactions = self._user_transactions_query(db, current_user.id).order_by(Transaction.transaction_date.asc()).all()
        dashboard = self._build_cached_payloads(current_user.id, all_transactions, insights)
        return {
            "statementId": statement.id,
            "parsedCount": len(db_transactions),
            "skippedCount": len(raw_transactions) - len(db_transactions),
            "rawExtractedRows": len(raw_transactions),
            "dashboard": dashboard["summary"],
        }

    def fetch_dashboard(self, db: Session, current_user: User, include_transactions: bool = False) -> dict:
        cached = dashboard_cache.get_transactions(current_user.id) if include_transactions else dashboard_cache.get_summary(current_user.id)
        if cached:
            return cached

        transactions = self._user_transactions_query(db, current_user.id).order_by(Transaction.transaction_date.asc()).all()
        if not transactions:
            dashboard = empty_dashboard_payload()
            dashboard["supportedBanks"] = get_supported_banks_payload()
            return dashboard
        payloads = self._build_cached_payloads(current_user.id, transactions, insights="")
        return payloads["transactions" if include_transactions else "summary"]

    def update_transaction_type(self, db: Session, current_user: User, transaction_id: int, transaction_type: str) -> dict:
        transaction = self._user_transactions_query(db, current_user.id).filter(Transaction.id == transaction_id).first()
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found.")

        transaction.transaction_type = transaction_type
        db.commit()
        db.refresh(transaction)

        dashboard_cache.clear(current_user.id)
        dashboard = self.fetch_dashboard(db, current_user, include_transactions=True)
        self._refresh_retriever_index(db, current_user.id)
        return {"message": "Transaction type updated successfully.", "dashboard": dashboard}

    def update_transaction_category(self, db: Session, current_user: User, transaction_id: int, category: str) -> dict:
        if category not in CATEGORIES:
            raise HTTPException(status_code=400, detail="Invalid category.")

        transaction = self._user_transactions_query(db, current_user.id).filter(Transaction.id == transaction_id).first()
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found.")

        target_signature = build_description_signature(transaction.description or "")
        updated_count = 0

        for candidate in self._user_transactions_query(db, current_user.id).all():
            if build_description_signature(candidate.description or "") == target_signature:
                candidate.category = category
                updated_count += 1

        db.commit()
        dashboard_cache.clear(current_user.id)
        dashboard = self.fetch_dashboard(db, current_user, include_transactions=True)
        self._refresh_retriever_index(db, current_user.id)
        return {
            "message": f"Category updated successfully for {updated_count} similar transaction(s).",
            "dashboard": dashboard,
        }

    def _extract_rows(self, file_bytes: bytes, bank_name: str) -> list[list[str]]:
        specialized_rows = extract_bank_rows(file_bytes, bank_name)
        if specialized_rows:
            return specialized_rows
        return extract_rows_from_pdf(file_bytes)

    def _build_cached_payloads(self, user_id: int, transactions: list[Transaction], insights: str) -> dict[str, dict]:
        summary_payload = build_dashboard_payload(transactions, insights, include_transactions=False)
        summary_payload["supportedBanks"] = get_supported_banks_payload()

        transactions_payload = build_dashboard_payload(transactions, insights, include_transactions=True)
        transactions_payload["supportedBanks"] = get_supported_banks_payload()

        dashboard_cache.set(user_id, summary_payload, transactions_payload)
        return {"summary": summary_payload, "transactions": transactions_payload}

    def _refresh_retriever_index(self, db: Session, user_id: int) -> None:
        try:
            self.retriever.rebuild_index(db, user_id)
        except Exception as exc:
            logger.warning("RAG index rebuild skipped after data update: %s", exc)

    def _user_transactions_query(self, db: Session, user_id: int):
        return db.query(Transaction).join(Transaction.statement).filter(Statement.user_id == user_id)
