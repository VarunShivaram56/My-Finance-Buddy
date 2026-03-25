import logging

from pydantic import BaseModel
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from database.models import User
from database.session import get_db
from rag.retriever import FinanceRetriever
from routers.auth_router import get_current_user
from services.bank_profiles import get_supported_banks_payload
from services.statement_service import StatementService


class TransactionTypeUpdatePayload(BaseModel):
    transactionId: int
    transactionType: str


class TransactionCategoryUpdatePayload(BaseModel):
    transactionId: int
    category: str


class NonBankingTransactionCreatePayload(BaseModel):
    transactionDate: str
    beneficiary: str
    description: str = ""
    transactionType: str
    category: str
    amount: float


router = APIRouter()
statement_service = StatementService()
retriever = FinanceRetriever()
logger = logging.getLogger(__name__)


@router.post("/upload-statement")
async def upload_statement(
    file: UploadFile = File(...),
    bank_name: str = Form("karnataka_bank"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    if file.content_type not in {"application/pdf", "application/octet-stream"} and not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        result = statement_service.process_statement(db, current_user, file.filename, file_bytes, bank_name=bank_name)
        try:
            retriever.rebuild_index(db, current_user.id)
        except Exception as exc:
            logger.warning("RAG index rebuild skipped after upload: %s", exc)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Statement upload failed: %s", exc)
        raise HTTPException(status_code=500, detail="Statement processing failed. Please try again.") from exc


@router.get("/dashboard")
def get_dashboard(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict:
    return statement_service.fetch_dashboard(db, current_user)


@router.get("/transactions")
def get_transactions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict:
    return statement_service.fetch_dashboard(db, current_user, include_transactions=True)


@router.get("/supported-banks")
def get_supported_banks() -> dict:
    return {"supportedBanks": get_supported_banks_payload()}


@router.patch("/update-transaction-type")
def update_transaction_type(
    payload: TransactionTypeUpdatePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    if payload.transactionType not in {"debit", "credit"}:
        raise HTTPException(status_code=400, detail="Transaction type must be debit or credit.")
    result = statement_service.update_transaction_type(db, current_user, payload.transactionId, payload.transactionType)
    return result


@router.patch("/update-transaction-category")
def update_transaction_category(
    payload: TransactionCategoryUpdatePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return statement_service.update_transaction_category(db, current_user, payload.transactionId, payload.category)


@router.post("/non-banking-transactions")
def create_non_banking_transaction(
    payload: NonBankingTransactionCreatePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return statement_service.add_non_banking_transaction(
        db,
        current_user,
        payload.transactionDate,
        payload.beneficiary,
        payload.amount,
        payload.transactionType,
        payload.category,
        payload.description,
    )
