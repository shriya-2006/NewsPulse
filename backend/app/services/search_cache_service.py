"""
Cache-aside logic for news search: check the DB for a fresh-enough
cached result set before calling out to a live provider, and store
whatever a live search returns so the next matching search can be
served from the database instead.

This intentionally caches the FULL result set for a query (not just one
page) — pagination happens over the cached article list the same way it
already happens over a live provider's results, so page 2 of a cached
search doesn't require re-fetching anything.
"""

import hashlib
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.cached_search import CachedSearch, cached_search_articles
from app.models.report import Article
from app.services.news.base import NormalizedArticle


def build_cache_key(
    *,
    keyword: str,
    language: str,
    newspaper: str | None,
    edition: str | None,
    date_filter: str,
    date_from: date | None,
    date_to: date | None,
) -> str:
    """
    A deterministic fingerprint of every parameter that affects search
    results. Keyword is lowercased/trimmed so "Steel" and " steel " hit
    the same cache entry. "today"/"yesterday" resolve to the actual
    calendar date as part of the key, so a cache entry from yesterday's
    "today" search doesn't get reused as if it still meant today.
    """
    resolved_from, resolved_to = date_from, date_to
    if date_filter == "today":
        resolved_from = resolved_to = date.today()
    elif date_filter == "yesterday":
        resolved_from = resolved_to = date.today() - timedelta(days=1)

    raw = "|".join(
        [
            keyword.strip().lower(),
            language,
            (newspaper or "").lower(),
            (edition or "").lower(),
            date_filter,
            resolved_from.isoformat() if resolved_from else "",
            resolved_to.isoformat() if resolved_to else "",
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def get_fresh_cached_search(db: Session, cache_key: str) -> CachedSearch | None:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.SEARCH_CACHE_FRESHNESS_HOURS)
    entry = db.query(CachedSearch).filter(CachedSearch.cache_key == cache_key).first()
    if entry is None:
        return None

    fetched_at = entry.fetched_at
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=timezone.utc)
    if fetched_at < cutoff:
        return None  # exists, but stale — caller should refresh it

    return entry


def _get_or_create_article(db: Session, article: NormalizedArticle) -> Article:
    existing = db.query(Article).filter(Article.url == article.url).first()
    if existing:
        return existing

    row = Article(
        source_name=article.source_name,
        title=article.title,
        url=article.url,
        description=article.description,
        image_url=article.image_url,
        content=article.content,
        language=article.language,
        published_at=article.published_at,
    )
    db.add(row)
    db.flush()  # assigns row.id for the join-table insert below
    return row


def store_search_result(
    db: Session,
    *,
    cache_key: str,
    keyword: str,
    language: str,
    newspaper: str | None,
    edition: str | None,
    date_filter: str,
    provider_used: str | None,
    articles: list[NormalizedArticle],
) -> CachedSearch:
    """
    Upserts a CachedSearch row for this cache_key and (re)links it to
    the given articles, replacing whatever it pointed to before — a
    refreshed search fully replaces its own prior cached result set
    rather than accumulating stale links alongside new ones.
    """
    entry = db.query(CachedSearch).filter(CachedSearch.cache_key == cache_key).first()
    if entry is None:
        entry = CachedSearch(
            cache_key=cache_key,
            keyword=keyword,
            language=language,
            newspaper=newspaper,
            edition=edition,
            date_filter=date_filter,
            provider_used=provider_used,
            result_count=len(articles),
            fetched_at=datetime.now(timezone.utc),
        )
        db.add(entry)
        db.flush()
    else:
        entry.provider_used = provider_used
        entry.result_count = len(articles)
        entry.fetched_at = datetime.now(timezone.utc)
        # Drop the old article links before adding the fresh ones —
        # this cache entry now represents a brand new fetch.
        db.execute(delete(cached_search_articles).where(cached_search_articles.c.cached_search_id == entry.id))
        db.flush()

    for position, article in enumerate(articles):
        article_row = _get_or_create_article(db, article)
        db.execute(
            cached_search_articles.insert().values(
                cached_search_id=entry.id, article_id=article_row.id, position=position
            )
        )

    db.commit()
    db.refresh(entry)
    return entry


def cached_articles_as_normalized(entry: CachedSearch) -> list[NormalizedArticle]:
    """Converts a CachedSearch's linked Article rows back into
    NormalizedArticle, so the route can treat a cache hit identically
    to a live provider result."""
    results = []
    for a in entry.articles:
        published_at = a.published_at
        if published_at is not None and published_at.tzinfo is None:
            # MySQL/SQLite DATETIME columns don't retain timezone info —
            # every published_at this app ever writes is UTC (see
            # aggregator.py's _within_range and the individual providers),
            # so reattaching it here keeps a cached result indistinguishable
            # from a freshly-fetched one instead of silently becoming
            # naive after a round trip through the database.
            published_at = published_at.replace(tzinfo=timezone.utc)

        results.append(
            NormalizedArticle(
                title=a.title,
                source_name=a.source_name,
                url=a.url,
                description=a.description,
                image_url=a.image_url,
                published_at=published_at,
                language=a.language,
                content=a.content,
            )
        )
    return results
