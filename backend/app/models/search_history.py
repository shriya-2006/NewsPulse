"""
One row per search a user runs — powers their own history later and the
admin dashboard's "total searches" / "most searched keywords" metrics.
Mirrors the `search_history` table in database/schema.sql.
"""

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.user import BigIntFK, BigIntPK


class SearchHistory(Base):
    __tablename__ = "search_history"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigIntFK, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    keyword: Mapped[str] = mapped_column(String(255), nullable=False)
    language: Mapped[str] = mapped_column(Enum("en", "te", "hi", name="search_language"), nullable=False, default="en")
    newspaper: Mapped[str | None] = mapped_column(String(100), nullable=True)
    edition: Mapped[str | None] = mapped_column(String(100), nullable=True)
    result_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    searched_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user = relationship("User")
