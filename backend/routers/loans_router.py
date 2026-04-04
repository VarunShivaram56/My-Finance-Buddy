from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.models import Loan, User
from database.session import get_db
from routers.auth_router import get_current_user
from services.dashboard_cache import dashboard_cache


class CreateLoanPayload(BaseModel):
    loan_name: str = Field(min_length=1, max_length=255)
    lender: str = Field(min_length=1, max_length=255)
    principal_amount: float = Field(gt=0)
    interest_rate: float = Field(ge=0)
    tenure_months: int = Field(gt=0)
    emi_amount: float = Field(ge=0, default=0)
    start_date: date
    notes: Optional[str] = None


class UpdateLoanPayload(BaseModel):
    loan_name: Optional[str] = None
    lender: Optional[str] = None
    principal_amount: Optional[float] = None
    interest_rate: Optional[float] = None
    tenure_months: Optional[int] = None
    emi_amount: Optional[float] = None
    total_paid: Optional[float] = None
    status: Optional[str] = None
    notes: Optional[str] = None


router = APIRouter(prefix="/loans", tags=["loans"])


def _serialize_loan(loan: Loan) -> dict:
    remaining = max(loan.principal_amount - loan.total_paid, 0)
    
    if loan.emi_amount and loan.emi_amount * loan.tenure_months >= loan.principal_amount:
        total_payable = loan.emi_amount * loan.tenure_months
    else:
        r = (loan.interest_rate / 100.0) / 12.0
        if r > 0:
            calc_emi = loan.principal_amount * r * ((1 + r)**loan.tenure_months) / (((1 + r)**loan.tenure_months) - 1)
            total_payable = calc_emi * loan.tenure_months
        else:
            total_payable = loan.principal_amount
            
    total_interest = max(total_payable - loan.principal_amount, 0)
    completion_pct = min(100.0, round((loan.total_paid / total_payable * 100) if total_payable > 0 else 0, 1))

    months_elapsed = 0
    if loan.emi_amount > 0 and loan.total_paid > 0:
        months_elapsed = int(loan.total_paid / loan.emi_amount)
    months_remaining = max(loan.tenure_months - months_elapsed, 0)

    return {
        "id": loan.id,
        "loanName": loan.loan_name,
        "lender": loan.lender,
        "principalAmount": loan.principal_amount,
        "interestRate": loan.interest_rate,
        "tenureMonths": loan.tenure_months,
        "emiAmount": loan.emi_amount,
        "startDate": loan.start_date.isoformat() if loan.start_date else "",
        "totalPaid": loan.total_paid,
        "status": loan.status,
        "notes": loan.notes or "",
        "remainingBalance": round(remaining, 2),
        "totalInterest": round(total_interest, 2),
        "totalPayable": round(total_payable, 2),
        "completionPercentage": completion_pct,
        "monthsRemaining": months_remaining,
    }


def _compute_summary(loans: list[Loan]) -> dict:
    active_loans = [loan for loan in loans if loan.status == "active"]
    total_outstanding = sum(max(loan.principal_amount - loan.total_paid, 0) for loan in active_loans)
    monthly_emi_burden = sum(loan.emi_amount for loan in active_loans)
    total_principal = sum(loan.principal_amount for loan in active_loans)
    total_paid = sum(loan.total_paid for loan in active_loans)

    total_payable = 0
    total_interest = 0
    for loan in active_loans:
        if loan.emi_amount and loan.emi_amount * loan.tenure_months >= loan.principal_amount:
            loan_payable = loan.emi_amount * loan.tenure_months
        else:
            r = (loan.interest_rate / 100.0) / 12.0
            if r > 0:
                calc_emi = loan.principal_amount * r * ((1 + r)**loan.tenure_months) / (((1 + r)**loan.tenure_months) - 1)
                loan_payable = calc_emi * loan.tenure_months
            else:
                loan_payable = loan.principal_amount
        total_payable += loan_payable
        total_interest += max(loan_payable - loan.principal_amount, 0)

    avg_completion = (
        min(100.0, round(total_paid / total_payable * 100, 1)) if total_payable > 0 else 0
    )

    return {
        "totalOutstanding": round(total_outstanding, 2),
        "monthlyEmiBurden": round(monthly_emi_burden, 2),
        "totalLoansCount": len(loans),
        "activeLoansCount": len(active_loans),
        "completionRate": avg_completion,
        "totalInterestPayable": round(total_interest, 2),
    }


@router.get("")
def list_loans(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    loans = db.query(Loan).filter(Loan.user_id == current_user.id).order_by(Loan.created_at.desc()).all()
    return {
        "loans": [_serialize_loan(loan) for loan in loans],
        "summary": _compute_summary(loans),
    }


@router.post("")
def create_loan(
    payload: CreateLoanPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    loan = Loan(
        user_id=current_user.id,
        loan_name=payload.loan_name.strip(),
        lender=payload.lender.strip(),
        principal_amount=payload.principal_amount,
        interest_rate=payload.interest_rate,
        tenure_months=payload.tenure_months,
        emi_amount=payload.emi_amount,
        start_date=payload.start_date,
        total_paid=0,
        status="active",
        notes=(payload.notes or "").strip() or None,
    )
    db.add(loan)
    db.commit()
    db.refresh(loan)

    dashboard_cache.clear(current_user.id)
    loans = db.query(Loan).filter(Loan.user_id == current_user.id).order_by(Loan.created_at.desc()).all()
    return {
        "message": f"Loan '{loan.loan_name}' added successfully.",
        "loans": [_serialize_loan(l) for l in loans],
        "summary": _compute_summary(loans),
    }


@router.patch("/{loan_id}")
def update_loan(
    loan_id: int,
    payload: UpdateLoanPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    loan = db.query(Loan).filter(Loan.id == loan_id, Loan.user_id == current_user.id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found.")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(loan, field, value)
    db.commit()
    db.refresh(loan)

    dashboard_cache.clear(current_user.id)
    loans = db.query(Loan).filter(Loan.user_id == current_user.id).order_by(Loan.created_at.desc()).all()
    return {
        "message": f"Loan '{loan.loan_name}' updated.",
        "loans": [_serialize_loan(l) for l in loans],
        "summary": _compute_summary(loans),
    }


@router.delete("/{loan_id}")
def delete_loan(
    loan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    loan = db.query(Loan).filter(Loan.id == loan_id, Loan.user_id == current_user.id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found.")

    loan_name = loan.loan_name
    db.delete(loan)
    db.commit()

    dashboard_cache.clear(current_user.id)
    loans = db.query(Loan).filter(Loan.user_id == current_user.id).order_by(Loan.created_at.desc()).all()
    return {
        "message": f"Loan '{loan_name}' has been deleted.",
        "loans": [_serialize_loan(l) for l in loans],
        "summary": _compute_summary(loans),
    }
