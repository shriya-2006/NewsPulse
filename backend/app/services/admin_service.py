"""
Admin dashboard business logic — all read-only aggregate queries over
existing tables (users, search_history, reports). No separate analytics
table: at this scale, GROUP BY / COUNT queries are simpler to reason
about and can't drift out of sync with the source data.
"""

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.report import Report
from app.models.search_history import SearchHistory
from app.models.user import User
from app.services import newspaper_service

# A user counts as "active" if they've logged in within this window.
# No single universally-correct definition exists for this — this is a
# reasonable default for an internal tool with daily/weekly usage
# patterns; worth revisiting once real usage data exists.
ACTIVE_USER_WINDOW_DAYS = 30

# How many rows to show in each "recent" / "top N" list.
RECENT_LIMIT = 10
TOP_N_LIMIT = 10
DAILY_WINDOW_DAYS = 14
MONTHLY_WINDOW_MONTHS = 12


def get_overview(db: Session) -> dict:
    total_users = db.query(func.count(User.id)).scalar() or 0

    active_cutoff = datetime.now(timezone.utc) - timedelta(days=ACTIVE_USER_WINDOW_DAYS)
    active_users = (
        db.query(func.count(User.id)).filter(User.last_login_at >= active_cutoff).scalar() or 0
    )

    total_searches = db.query(func.count(SearchHistory.id)).scalar() or 0
    total_reports = db.query(func.count(Report.id)).scalar() or 0

    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_searches": total_searches,
        "total_reports": total_reports,
    }


def get_recent_searches(db: Session, limit: int = RECENT_LIMIT) -> list[dict]:
    rows = (
        db.query(SearchHistory, User.full_name)
        .join(User, User.id == SearchHistory.user_id)
        .order_by(SearchHistory.searched_at.desc())
        .limit(limit)
        .all()
    )
    def _newspaper_label(key: str | None) -> str | None:
        if not key:
            return None
        newspaper = newspaper_service.get_newspaper_by_key(db, key)
        return newspaper.label if newspaper else key

    return [
        {
            "id": sh.id,
            "user_full_name": full_name,
            "keyword": sh.keyword,
            "language": sh.language,
            "newspaper": _newspaper_label(sh.newspaper),
            "result_count": sh.result_count,
            "searched_at": sh.searched_at,
        }
        for sh, full_name in rows
    ]


def get_recent_reports(db: Session, limit: int = RECENT_LIMIT) -> list[dict]:
    rows = (
        db.query(Report, User.full_name)
        .join(User, User.id == Report.user_id)
        .order_by(Report.generated_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "user_full_name": full_name,
            "title": r.title,
            "article_count": r.article_count,
            "generated_at": r.generated_at,
        }
        for r, full_name in rows
    ]


def get_most_searched_keywords(db: Session, limit: int = TOP_N_LIMIT) -> list[dict]:
    # Grouped case-sensitively for simplicity/portability (MySQL's
    # ONLY_FULL_GROUP_BY mode rejects selecting a non-aggregated column
    # that isn't in the GROUP BY, which a case-insensitive grouping would
    # require working around) — "Steel" and "steel" are counted separately.
    rows = (
        db.query(SearchHistory.keyword, func.count(SearchHistory.id).label("cnt"))
        .group_by(SearchHistory.keyword)
        .order_by(func.count(SearchHistory.id).desc())
        .limit(limit)
        .all()
    )
    return [{"label": keyword, "count": cnt} for keyword, cnt in rows]


def get_most_selected_language(db: Session) -> list[dict]:
    rows = (
        db.query(SearchHistory.language, func.count(SearchHistory.id).label("cnt"))
        .group_by(SearchHistory.language)
        .order_by(func.count(SearchHistory.id).desc())
        .all()
    )
    labels = {"en": "English", "te": "Telugu", "hi": "Hindi"}
    return [{"label": labels.get(lang, lang), "count": cnt} for lang, cnt in rows]


def get_most_selected_newspaper(db: Session, limit: int = TOP_N_LIMIT) -> list[dict]:
    rows = (
        db.query(SearchHistory.newspaper, func.count(SearchHistory.id).label("cnt"))
        .filter(SearchHistory.newspaper.isnot(None))
        .group_by(SearchHistory.newspaper)
        .order_by(func.count(SearchHistory.id).desc())
        .limit(limit)
        .all()
    )
    results = []
    for key, cnt in rows:
        newspaper = newspaper_service.get_newspaper_by_key(db, key)
        results.append({"label": newspaper.label if newspaper else key, "count": cnt})
    return results


def get_most_selected_edition(db: Session, limit: int = TOP_N_LIMIT) -> list[dict]:
    rows = (
        db.query(SearchHistory.edition, func.count(SearchHistory.id).label("cnt"))
        .filter(SearchHistory.edition.isnot(None))
        .group_by(SearchHistory.edition)
        .order_by(func.count(SearchHistory.id).desc())
        .limit(limit)
        .all()
    )
    return [{"label": edition, "count": cnt} for edition, cnt in rows]


def get_daily_reports(db: Session, days: int = DAILY_WINDOW_DAYS) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        db.query(Report.generated_at)
        .filter(Report.generated_at >= since)
        .all()
    )
    counts: dict[str, int] = defaultdict(int)
    for (generated_at,) in rows:
        counts[generated_at.strftime("%Y-%m-%d")] += 1

    # Fill in every day in the window (including zero-report days) so the
    # frontend chart doesn't have to guess at gaps.
    today = datetime.now(timezone.utc).date()
    series = []
    for i in range(days - 1, -1, -1):
        day = today - timedelta(days=i)
        key = day.strftime("%Y-%m-%d")
        series.append({"period": key, "count": counts.get(key, 0)})
    return series


def get_monthly_reports(db: Session, months: int = MONTHLY_WINDOW_MONTHS) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=months * 31)
    rows = db.query(Report.generated_at).filter(Report.generated_at >= since).all()

    counts: dict[str, int] = defaultdict(int)
    for (generated_at,) in rows:
        counts[generated_at.strftime("%Y-%m")] += 1

    # Build the last `months` year-month buckets in order, zero-filled.
    now = datetime.now(timezone.utc)
    series = []
    year, month = now.year, now.month
    buckets = []
    for _ in range(months):
        buckets.append(f"{year:04d}-{month:02d}")
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    for key in reversed(buckets):
        series.append({"period": key, "count": counts.get(key, 0)})
    return series


def get_users_with_activity(db: Session) -> list[dict]:
    search_counts = dict(
        db.query(SearchHistory.user_id, func.count(SearchHistory.id))
        .group_by(SearchHistory.user_id)
        .all()
    )
    report_counts = dict(
        db.query(Report.user_id, func.count(Report.id)).group_by(Report.user_id).all()
    )

    users = db.query(User).order_by(User.created_at.desc()).all()
    return [
        {
            "id": u.id,
            "full_name": u.full_name,
            "email": u.email,
            "is_admin": u.is_admin,
            "is_active": u.is_active,
            "search_count": search_counts.get(u.id, 0),
            "report_count": report_counts.get(u.id, 0),
            "last_login_at": u.last_login_at,
            "created_at": u.created_at,
        }
        for u in users
    ]


def get_full_dashboard(db: Session) -> dict:
    return {
        "overview": get_overview(db),
        "recent_searches": get_recent_searches(db),
        "recent_reports": get_recent_reports(db),
        "most_searched_keywords": get_most_searched_keywords(db),
        "most_selected_language": get_most_selected_language(db),
        "most_selected_newspaper": get_most_selected_newspaper(db),
        "most_selected_edition": get_most_selected_edition(db),
        "daily_reports": get_daily_reports(db),
        "monthly_reports": get_monthly_reports(db),
    }
