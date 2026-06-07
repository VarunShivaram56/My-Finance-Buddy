from __future__ import annotations

import hashlib
import logging
from datetime import date

from sqlalchemy.orm import Session

from fastapi import HTTPException

from agents.agent_manager import AgentManager
from database.models import Loan, NonBankingTransaction, RawStatementLine, Statement, Transaction, User
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

        # Agent 1: enrich only low-confidence rows (merchant extraction only)
        enriched = self.agent_manager.enrich_low_confidence(raw_transactions, parsed)
        for index, llm_row in enumerate(enriched):
            if not llm_row:
                continue
            # Agent 1 now returns merchant-only enrichment; keep deterministic
            # values for date/amount/type which the parser handles reliably.
            if llm_row.get("merchant") and not parsed[index].merchant:
                parsed[index].merchant = llm_row["merchant"]
            # Upgrade confidence when LLM successfully identified a merchant
            if llm_row.get("merchant"):
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
            raw_line = RawStatementLine(
                statement_id=statement.id,
                raw_text=transaction.raw_text or "",
                parser_confidence=transaction.confidence
            )
            db.add(raw_line)
            db.flush()

            db_transaction = Transaction(
                raw_line_id=raw_line.id,
                statement_id=statement.id,
                transaction_date=transaction_date,
                merchant=transaction.merchant or "Unknown",
                amount=transaction.amount or 0,
                transaction_type=transaction.transaction_type or "debit",
                category=category,
                description=transaction.description,
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
        non_banking_transactions = self._user_non_banking_transactions_query(db, current_user.id).order_by(
            NonBankingTransaction.transaction_date.asc()
        ).all()
        loans = db.query(Loan).filter(Loan.user_id == current_user.id).all()
        dashboard = self._build_cached_payloads(current_user.id, all_transactions, non_banking_transactions, insights, loans)
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
        non_banking_transactions = self._user_non_banking_transactions_query(db, current_user.id).order_by(
            NonBankingTransaction.transaction_date.asc()
        ).all()
        loans = db.query(Loan).filter(Loan.user_id == current_user.id).all()
        if not transactions and not non_banking_transactions and not loans:
            dashboard = empty_dashboard_payload()
            dashboard["supportedBanks"] = get_supported_banks_payload()
            return dashboard
        payloads = self._build_cached_payloads(current_user.id, transactions, non_banking_transactions, insights="", loans=loans)
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
        return {
            "message": f"Category updated successfully for {updated_count} similar transaction(s).",
            "dashboard": dashboard,
        }

    def add_non_banking_transaction(
        self,
        db: Session,
        current_user: User,
        transaction_date: str,
        beneficiary: str,
        amount: float,
        transaction_type: str,
        category: str,
        description: str | None = None,
    ) -> dict:
        try:
            parsed_date = date.fromisoformat(transaction_date)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Enter a valid transaction date.") from exc

        beneficiary_name = beneficiary.strip()
        if len(beneficiary_name) < 2:
            raise HTTPException(status_code=400, detail="Beneficiary name must be at least 2 characters long.")
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be greater than zero.")
        if transaction_type not in {"debit", "credit"}:
            raise HTTPException(status_code=400, detail="Transaction type must be debit or credit.")
        if category not in CATEGORIES:
            raise HTTPException(status_code=400, detail="Invalid category.")

        transaction = NonBankingTransaction(
            user_id=current_user.id,
            transaction_date=parsed_date,
            beneficiary=beneficiary_name[:255],
            amount=round(amount, 2),
            transaction_type=transaction_type,
            category=category,
            description=(description or "").strip() or None,
        )
        db.add(transaction)
        db.commit()
        db.refresh(transaction)

        dashboard_cache.clear(current_user.id)
        dashboard = self.fetch_dashboard(db, current_user, include_transactions=True)
        return {
            "message": "Non-banking transaction added successfully.",
            "dashboard": dashboard,
        }

    def _extract_rows(self, file_bytes: bytes, bank_name: str) -> list[list[str]]:
        specialized_rows = extract_bank_rows(file_bytes, bank_name)
        if specialized_rows:
            return specialized_rows
        return extract_rows_from_pdf(file_bytes)

    def _build_cached_payloads(
        self,
        user_id: int,
        transactions: list[Transaction],
        non_banking_transactions: list[NonBankingTransaction],
        insights: str,
        loans: list[Loan] | None = None,
    ) -> dict[str, dict]:
        summary_payload = build_dashboard_payload(
            transactions,
            insights,
            include_transactions=False,
            non_banking_transactions=non_banking_transactions,
            loans=loans,
        )
        summary_payload["supportedBanks"] = get_supported_banks_payload()

        transactions_payload = build_dashboard_payload(
            transactions,
            insights,
            include_transactions=True,
            non_banking_transactions=non_banking_transactions,
            loans=loans,
        )
        transactions_payload["supportedBanks"] = get_supported_banks_payload()

        dashboard_cache.set(user_id, summary_payload, transactions_payload)
        return {"summary": summary_payload, "transactions": transactions_payload}

    def _user_transactions_query(self, db: Session, user_id: int):
        return db.query(Transaction).join(Transaction.statement).filter(Statement.user_id == user_id)

    def _user_non_banking_transactions_query(self, db: Session, user_id: int):
        return db.query(NonBankingTransaction).filter(NonBankingTransaction.user_id == user_id)
