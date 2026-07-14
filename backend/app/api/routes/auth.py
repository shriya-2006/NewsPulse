"""
Auth routes: register, login, forgot/reset password, current-user, logout.

Kept thin on purpose — validation lives in schemas, business logic lives
in services/auth_service.py. This file's job is only to wire HTTP <-> service.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserOut,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    user = auth_service.register_user(db, payload)
    token, expires_in = auth_service.issue_token_for_user(user, remember_me=False)
    return TokenResponse(access_token=token, expires_in=expires_in, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = auth_service.authenticate_user(db, payload.email, payload.password)
    token, expires_in = auth_service.issue_token_for_user(user, payload.remember_me)
    return TokenResponse(access_token=token, expires_in=expires_in, user=UserOut.model_validate(user))


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    auth_service.start_password_reset(db, payload.email)
    # Same message whether or not the email exists — prevents account
    # enumeration via the forgot-password form.
    return MessageResponse(
        message="If an account exists for this email, a reset link has been sent."
    )


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    auth_service.reset_password(db, payload.token, payload.new_password)
    return MessageResponse(message="Your password has been reset. You can now sign in.")


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/logout", response_model=MessageResponse)
def logout(current_user: User = Depends(get_current_user)):
    # JWTs are stateless, so there's nothing to invalidate server-side yet.
    # This endpoint exists so the frontend has a consistent contract, and
    # so a later module (token blacklist / refresh tokens) has a clear home.
    # Still requires a valid token — an already-signed-out/invalid token
    # gets a 401, same as every other protected route, rather than a
    # silent 200 that implies the call did something it didn't.
    return MessageResponse(message="Signed out.")
