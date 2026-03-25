from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from database.session import get_db
from services.statement_service import StatementService


router = APIRouter()
statement_service = StatementService()


@router.post("/upload-statement")
async def upload_statement(file: UploadFile = File(...), db: Session = Depends(get_db)) -> dict:
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        return statement_service.process_statement(db, file.filename, file_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/dashboard")
def get_dashboard(db: Session = Depends(get_db)) -> dict:
    return statement_service.fetch_dashboard(db)
