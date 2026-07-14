"""
Standalone cleanup job: deletes cached search entries older than
SEARCH_CACHE_FRESHNESS_HOURS-times-over (i.e. genuinely old, not just
"needs a refresh"), then deletes cached Article rows that are both
old AND no longer referenced by anything — never selected into a
report, and not part of any remaining (still-recent) cached search.

Designed to be triggered by an OS-level or cloud-provider cron, not by
the FastAPI app itself — this keeps "the app is running" and "cleanup
happens on schedule" as two independent concerns. Run it with:

    python -m app.scripts.cleanup_old_articles

Wire this into:
- Windows: Task Scheduler, running that command daily
- Linux/Docker: a real crontab entry, e.g. `0 3 * * * ...`
- Render/Railway: their built-in "Cron Job" service type, pointed at
  this same command, on whatever schedule you like (daily is plenty
  given the retention window is measured in days/months, not hours)
"""

import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy import exists
from sqlalchemy.orm import Session

import app.db.database as dbmod
from app.core.config import settings
from app.models.cached_search import CachedSearch, cached_search_articles
from app.models.report import Article, report_articles


def run_cleanup(retention_days: int | None = None, db: Session | None = None) -> dict:
    """
    Returns a small summary dict — kept separate from print() statements
    so this is also callable/testable directly, not just from the
    command line.

    `db`: pass an existing session (e.g. from a FastAPI route's
    `Depends(get_db)`) to run the cleanup within that same
    session/transaction instead of opening a brand new one — this is
    what the admin "run cleanup now" endpoint does. When omitted (the
    standalone cron/script entrypoint), a fresh session is created via
    `dbmod.SessionLocal()` — accessed through the module object rather
    than imported by name, so it always reflects whatever the current
    real database configuration is, not whatever it was at the moment
    this module was first imported.
    """
    days = retention_days if retention_days is not None else settings.ARTICLE_RETENTION_DAYS
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    owns_session = db is None
    if db is None:
        db = dbmod.SessionLocal()

    try:
        # 1. Delete old cache index entries. Their cached_search_articles
        # join rows cascade automatically (ON DELETE CASCADE on the FK).
        deleted_searches = (
            db.query(CachedSearch)
            .filter(CachedSearch.fetched_at < cutoff)
            .delete(synchronize_session=False)
        )

        # 2. Delete old articles that are no longer referenced by
        # anything — not part of any report (ever, regardless of the
        # report's own age — a generated PDF's underlying article data
        # is kept for as long as the report itself exists), and not
        # part of any cached search that's still within the retention
        # window (i.e. wasn't just deleted in step 1, or never was old
        # in the first place).
        still_in_report = exists().where(report_articles.c.article_id == Article.id)
        still_in_cache = exists().where(cached_search_articles.c.article_id == Article.id)

        deleted_articles = (
            db.query(Article)
            .filter(Article.fetched_at < cutoff)
            .filter(~still_in_report)
            .filter(~still_in_cache)
            .delete(synchronize_session=False)
        )

        db.commit()
    finally:
        if owns_session:
            db.close()

    return {
        "retention_days": days,
        "cutoff": cutoff.isoformat(),
        "deleted_cached_searches": deleted_searches,
        "deleted_articles": deleted_articles,
    }


if __name__ == "__main__":
    result = run_cleanup()
    print(
        f"[NewsPulse cleanup] retention={result['retention_days']}d "
        f"cutoff={result['cutoff']} "
        f"deleted_cached_searches={result['deleted_cached_searches']} "
        f"deleted_articles={result['deleted_articles']}"
    )
    sys.exit(0)
