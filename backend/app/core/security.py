"""
Security primitives: password hashing and JWT encode/decode.

Kept separate from services/routes so that (a) it has zero FastAPI/DB
imports and (b) it's trivially unit-testable on its own.
"""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


# ---------------------------------------------------------------------------
# JWT access tokens
# ---------------------------------------------------------------------------
def create_access_token(subject: str, expires_minutes: int) -> tuple[str, int]:
    """
    Returns (token, expires_in_seconds).

    `subject` is the value stored in the `sub` claim — we use the user's
    id (as a string, per JWT spec convention).
    """
    expire_delta = timedelta(minutes=expires_minutes)
    expire_at = datetime.now(timezone.utc) + expire_delta
    payload = {"sub": subject, "exp": expire_at}
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token, int(expire_delta.total_seconds())


def decode_access_token(token: str) -> dict | None:
    """Returns the decoded payload, or None if the token is invalid/expired."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None


# ---------------------------------------------------------------------------
# Password-reset tokens
# ---------------------------------------------------------------------------
def generate_reset_token() -> str:
    """A random, URL-safe, unguessable token for the forgot-password flow."""
    import secrets

    return secrets.token_urlsafe(32)
