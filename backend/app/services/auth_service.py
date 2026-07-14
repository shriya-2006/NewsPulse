"""
Auth business logic.

Routes (app/api/routes/auth.py) stay thin — they parse the request,
call a service function, and shape the response. All the actual rules
(uniqueness checks, password verification, token lifetimes, reset-token
expiry) live here so they're testable independently of FastAPI and
reusable if a second entrypoint (e.g. an admin CLI) ever needs them.
"""

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    generate_reset_token,
    hash_password,
    verify_password,
)
from app.models.user import PasswordResetToken, User
from app.schemas.auth import RegisterRequest
from app.services.email_service import send_password_reset_email

# How long a password-reset link stays valid.
RESET_TOKEN_EXPIRE_MINUTES = 30


def register_user(db: Session, payload: RegisterRequest) -> User:
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = User(
        full_name=payload.full_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    user = db.query(User).filter(User.email == email).first()

    # Deliberately identical error for "no such user" and "wrong password"
    # so the API never reveals whether an email is registered.
    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email or password.",
    )

    if not user or not verify_password(password, user.password_hash):
        raise invalid_credentials

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated. Contact your administrator.",
        )

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    return user


def issue_token_for_user(user: User, remember_me: bool) -> tuple[str, int]:
    expire_minutes = (
        settings.REMEMBER_ME_EXPIRE_MINUTES
        if remember_me
        else settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    return create_access_token(subject=str(user.id), expires_minutes=expire_minutes)


def start_password_reset(db: Session, email: str) -> str | None:
    """
    Creates a reset token for the user if one exists with this email.

    Returns the raw token (to be emailed) or None if no account matches.
    The route layer must NOT reveal which case occurred in its response —
    it always returns the same generic message either way.
    """
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None

    token = generate_reset_token()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)

    reset_row = PasswordResetToken(
        user_id=user.id,
        token=token,
        expires_at=expires_at,
    )
    db.add(reset_row)
    db.commit()

    send_password_reset_email(to_email=email, token=token)

    return token


def reset_password(db: Session, token: str, new_password: str) -> None:
    reset_row = (
        db.query(PasswordResetToken).filter(PasswordResetToken.token == token).first()
    )

    invalid_token = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="This reset link is invalid or has expired. Please request a new one.",
    )

    if not reset_row:
        raise invalid_token

    now = datetime.now(timezone.utc)
    expires_at = reset_row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if reset_row.used or expires_at < now:
        raise invalid_token

    user = db.query(User).filter(User.id == reset_row.user_id).first()
    if not user:
        raise invalid_token

    user.password_hash = hash_password(new_password)
    reset_row.used = True
    db.commit()
