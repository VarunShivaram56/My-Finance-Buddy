from __future__ import annotations

import hashlib
import hmac
import secrets


PBKDF2_ITERATIONS = 120_000


def generate_password_salt() -> str:
    return secrets.token_hex(16)


def hash_password(password: str, salt: str) -> str:
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS)
    return digest.hex()


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    candidate_hash = hash_password(password, salt)
    return hmac.compare_digest(candidate_hash, expected_hash)


def create_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
