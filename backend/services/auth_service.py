from __future__ import annotations

import re

from sqlalchemy.orm import Session

from fastapi import HTTPException

from database.models import User, UserSession
from services.auth_utils import create_session_token, generate_password_salt, hash_password, hash_session_token, verify_password


_USER_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_]{3,64}$")


class AuthService:
    def register(self, db: Session, name: str, user_id: str, password: str) -> dict:
        clean_user_id = user_id.strip()
        if not _USER_ID_PATTERN.match(clean_user_id):
            raise HTTPException(
                status_code=400,
                detail="User ID must be 3-64 characters long and contain only letters, numbers, or underscores.",
            )
        if len(name.strip()) < 2:
            raise HTTPException(status_code=400, detail="Name must be at least 2 characters long.")
        if db.query(User).filter(User.user_id == clean_user_id).first():
            raise HTTPException(status_code=400, detail="This user ID is already taken. Please choose another.")

        salt = generate_password_salt()
        user = User(
            name=name.strip(),
            user_id=clean_user_id,
            password_hash=hash_password(password, salt),
            password_salt=salt,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        token = self._create_session(db, user)
        return {"token": token, "user": _serialize_user(user)}

    def login(self, db: Session, user_id: str, password: str) -> dict:
        clean_user_id = user_id.strip()
        user = db.query(User).filter(User.user_id == clean_user_id).first()
        if not user or not verify_password(password, user.password_salt, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid user ID or password.")

        token = self._create_session(db, user)
        return {"token": token, "user": _serialize_user(user)}

    def logout(self, db: Session, token: str) -> None:
        token_hash = hash_session_token(token)
        session = db.query(UserSession).filter(UserSession.token_hash == token_hash).first()
        if session:
            db.delete(session)
            db.commit()

    def authenticate(self, db: Session, token: str) -> User:
        token_hash = hash_session_token(token)
        session = db.query(UserSession).filter(UserSession.token_hash == token_hash).first()
        if not session:
            raise HTTPException(status_code=401, detail="Authentication required.")
        user = db.query(User).filter(User.id == session.user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required.")
        return user

    def _create_session(self, db: Session, user: User) -> str:
        token = create_session_token()
        session = UserSession(user_id=user.id, token_hash=hash_session_token(token))
        db.add(session)
        db.commit()
        return token


def _serialize_user(user: User) -> dict[str, str | int]:
    return {"id": user.id, "name": user.name, "user_id": user.user_id}
