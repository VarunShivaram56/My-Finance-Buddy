from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from database.models import User
from database.session import get_db
from services.auth_service import AuthService


class RegisterPayload(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str
    password: str = Field(min_length=6, max_length=128)


class LoginPayload(BaseModel):
    email: str
    password: str = Field(min_length=6, max_length=128)


router = APIRouter(prefix="/auth", tags=["auth"])
auth_service = AuthService()


def get_current_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> User:
    token = _extract_bearer_token(authorization)
    return auth_service.authenticate(db, token)


def _extract_bearer_token(authorization: str | None, required: bool = True) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        if not required:
            return ""
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="Authentication required.")
    return authorization.split(" ", 1)[1].strip()


@router.post("/register")
def register(payload: RegisterPayload, db: Session = Depends(get_db)) -> dict:
    return auth_service.register(db, payload.name, payload.email, payload.password)


@router.post("/login")
def login(payload: LoginPayload, db: Session = Depends(get_db)) -> dict:
    return auth_service.login(db, payload.email, payload.password)


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)) -> dict:
    return {"user": {"id": current_user.id, "name": current_user.name, "email": current_user.email}}


@router.post("/logout")
def logout(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> dict:
    token = _extract_bearer_token(authorization, required=False)
    if token:
        auth_service.logout(db, token)
    return {"message": "Logged out successfully."}
