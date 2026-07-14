"""
Per-user custom search tags (the predefined industry tags — "Steel",
"RINL", etc. — are static data in app/utils/newspaper_sources.py, not
a table, since every user shares the same predefined list).
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.user import BigIntFK, BigIntPK


class CustomTag(Base):
    __tablename__ = "custom_tags"
    __table_args__ = (
        UniqueConstraint("user_id", "tag", name="uq_custom_tag_user_tag"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigIntFK, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    tag: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user = relationship("User")
