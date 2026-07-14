"""
Request/response schemas for the Auth module.

Kept separate from ORM models (app/models) on purpose: schemas describe
the HTTP contract (what a client sends/receives), models describe the
database table. They usually look similar but should never be the same
class — e.g. `password` only ever exists in a request schema, never in
a response schema, and never on the ORM model.
"""

import re

from pydantic import BaseModel, EmailStr, Field, field_validator

# A password must contain at least one letter and one number and be 8+
# characters. This is intentionally simple (no special-character
# requirement) to avoid frustrating users while still blocking trivial
# passwords like "12345678" or "password".
_PASSWORD_RULE = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,}$")


def _validate_password_strength(value: str) -> str:
    if not _PASSWORD_RULE.match(value):
        raise ValueError(
            "Password must be at least 8 characters and include at least "
            "one letter and one number."
        )
    return value


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------
class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150)
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        return _validate_password_strength(value)

    @field_validator("full_name")
    @classmethod
    def full_name_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Full name cannot be blank.")
        return value.strip()


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False


# ---------------------------------------------------------------------------
# Forgot / Reset password
# ---------------------------------------------------------------------------
class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        return _validate_password_strength(value)


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------
class UserOut(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    is_admin: bool

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: UserOut


class MessageResponse(BaseModel):
    message: str
