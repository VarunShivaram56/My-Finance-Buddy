from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.models import Statement, Transaction, User
from database.session import get_db
from rag.retriever import FinanceRetriever
from routers.auth_router import get_current_user
from services.bank_profiles import get_supported_banks_payload
from services.dashboard_cache import dashboard_cache
from services.stats import empty_dashboard_payload


router = APIRouter()
retriever = FinanceRetriever()


@router.delete("/reset-data")
def reset_data(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict:
    statements = db.query(Statement).filter(Statement.user_id == current_user.id).all()
    statement_ids = [statement.id for statement in statements]
    if statement_ids:
        db.query(Transaction).filter(Transaction.statement_id.in_(statement_ids)).delete(synchronize_session=False)
        db.query(Statement).filter(Statement.id.in_(statement_ids)).delete(synchronize_session=False)
    db.commit()
    dashboard_cache.clear(current_user.id)
    retriever.clear(current_user.id)
    dashboard = empty_dashboard_payload()
    dashboard["supportedBanks"] = get_supported_banks_payload()
    return {"message": "Data reset successfully.", "dashboard": dashboard}
