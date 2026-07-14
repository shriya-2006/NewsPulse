"""
Search-result caching: instead of hitting GNews/NewsData.io/Google News
RSS on every single search, a search's results are cached in the
database and served straight from there if a recent-enough cache entry
already exists for the exact same query. This matters most on free-tier
API keys (GNews: 100 requests/day, NewsData.io: 200/day) where two
people searching "steel" five minutes apart would otherwise both burn a
quota slot, and it also reduces how often the Google News RSS fallback
gets hit, which is the endpoint most likely to silently rate-limit
under heavy request volume.

Reuses the existing `articles` table as the article cache (already
used by report generation) — a CachedSearch just links a specific
query's result set to already-cached-or-freshly-cached Article rows.
"""

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.user import BigIntFK, BigIntPK

cached_search_articles = Table(
    "cached_search_articles",
    Base.metadata,
    Column(
        "cached_search_id",
        BigIntFK,
        ForeignKey("cached_searches.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("article_id", BigIntFK, ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True),
    # Preserves the provider's original result ordering when re-serving
    # a cached search — a plain many-to-many join has no inherent order.
    Column("position", Integer, nullable=False, default=0),
)


class CachedSearch(Base):
    """
    One row per distinct search query that's been run at least once.
    `cache_key` is a normalized, deterministic fingerprint of every
    parameter that affects results (keyword, language, newspaper,
    edition, and the resolved date range) — same query, same key,
    regardless of who ran it or in what order query params arrived.
    """

    __tablename__ = "cached_searches"
    __table_args__ = (UniqueConstraint("cache_key", name="uq_cached_search_key"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    cache_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    keyword: Mapped[str] = mapped_column(String(255), nullable=False)
    language: Mapped[str] = mapped_column(Enum("en", "te", "hi", name="cached_search_language"), nullable=False)
    newspaper: Mapped[str | None] = mapped_column(String(100), nullable=True)
    edition: Mapped[str | None] = mapped_column(String(100), nullable=True)
    date_filter: Mapped[str] = mapped_column(String(20), nullable=False)
    provider_used: Mapped[str | None] = mapped_column(String(20), nullable=True)
    result_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    articles: Mapped[list["Article"]] = relationship(  # noqa: F821
        secondary=cached_search_articles,
        order_by=cached_search_articles.c.position,
    )
