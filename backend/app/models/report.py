"""
Report generation models: a cached Article, a Report, and the
many-to-many join between them. Mirrors database/schema.sql exactly.
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
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.user import BigIntFK, BigIntPK

report_articles = Table(
    "report_articles",
    Base.metadata,
    Column("report_id", BigIntFK, ForeignKey("reports.id", ondelete="CASCADE"), primary_key=True),
    Column("article_id", BigIntFK, ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True),
)


class Article(Base):
    """
    A cached copy of a news article, created the moment it's first
    included in a report. Looked up by URL so the same article selected
    into two different reports doesn't get duplicated.
    """

    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(Enum("en", "te", "hi", name="article_language"), nullable=False, default="en")
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    reports: Mapped[list["Report"]] = relationship(
        secondary=report_articles, back_populates="articles"
    )


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigIntFK, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    keyword: Mapped[str] = mapped_column(String(255), nullable=False)
    language: Mapped[str] = mapped_column(Enum("en", "te", "hi", name="report_language"), nullable=False, default="en")
    newspaper: Mapped[str | None] = mapped_column(String(100), nullable=True)
    edition: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    article_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    generated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user = relationship("User")
    # Order here isn't guaranteed to match the report's PDF article order —
    # that's fixed at generation time from the request payload. This
    # relationship is only for later features like a report detail view.
    articles: Mapped[list["Article"]] = relationship(
        secondary=report_articles, back_populates="reports"
    )
