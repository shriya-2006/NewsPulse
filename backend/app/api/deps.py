"""
Shared FastAPI dependencies for authentication.

`get_current_user` is what every future protected route (search, reports,
admin) will depend on — e.g.:

    @router.get("/reports")
    def list_reports(user: User = Depends(get_current_user)):
        ...
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.database import get_db
from app.models.user import User

# tokenUrl points at the login route purely so /docs renders the "Authorize"
# button correctly — the frontend does not use OAuth2 password flow itself,
# it just sends `Authorization: Bearer <token>` after a normal JSON login.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_error

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise credentials_error

    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user or not user.is_active:
        raise credentials_error

    return user


def get_current_admin_user(user: User = Depends(get_current_user)) -> User:
    """For admin-only routes (Module 7 will use this)."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return user
