"""
Admin-only routes. Every route here depends on get_current_admin_user,
which 403s for any signed-in user whose `is_admin` flag isn't set.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.admin import AdminDashboardOut, CleanupResult, UsersListOut
from app.scripts.cleanup_old_articles import run_cleanup
from app.services import admin_service

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/dashboard", response_model=AdminDashboardOut)
def dashboard(
    _admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    return admin_service.get_full_dashboard(db)


@router.get("/users", response_model=UsersListOut)
def users(
    _admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    return UsersListOut(users=admin_service.get_users_with_activity(db))


@router.post("/cleanup-old-articles", response_model=CleanupResult)
def cleanup_old_articles(
    _admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Manually runs the same cleanup a scheduled cron job would (see
    app/scripts/cleanup_old_articles.py) — lets an admin trigger it
    on demand, e.g. for a demo, without needing real OS-level cron set
    up. In production this should also be scheduled to run
    automatically (daily is plenty) via Task Scheduler / crontab /
    your host's Cron Job feature, per that script's own docstring.
    """
    return run_cleanup(db=db)
