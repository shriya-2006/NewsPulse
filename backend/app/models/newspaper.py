"""
Newspaper + edition hierarchy, stored in the database rather than
hardcoded in the frontend (or even in backend Python) — per the
cascading-dropdown requirement, adding a new newspaper or edition is
just an INSERT, with zero frontend or backend code changes and zero
redeploys. The frontend only ever asks the API "what newspapers exist
for this language" and "what editions exist for this newspaper" — it
never has its own copy of this data.
"""

from sqlalchemy import Boolean, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.user import BigIntPK


class Newspaper(Base):
    __tablename__ = "newspapers"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    # Stable machine key used in URLs/query params (e.g. "the_hindu") —
    # separate from `label` so the display name can be edited without
    # breaking anything that already referenced this newspaper by key.
    key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    label: Mapped[str] = mapped_column(String(150), nullable=False)
    language: Mapped[str] = mapped_column(
        Enum("en", "te", "hi", name="newspaper_language"), nullable=False, index=True
    )
    # Used to restrict Google News RSS results to one outlet
    # (`site:thehindu.com steel plant`), since that's the only integrated
    # provider with no native "source" filter.
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    # Whether a provider can actually filter by the selected edition (none
    # of the three integrated providers support this today) — kept as a
    # column, not a constant, so it's accurate per-newspaper if that ever
    # changes for one specific source.
    edition_query_supported: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    editions: Mapped[list["NewspaperEdition"]] = relationship(
        back_populates="newspaper", cascade="all, delete-orphan", order_by="NewspaperEdition.name"
    )


class NewspaperEdition(Base):
    __tablename__ = "newspaper_editions"
    __table_args__ = (
        UniqueConstraint("newspaper_id", "name", name="uq_newspaper_edition_name"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    newspaper_id: Mapped[int] = mapped_column(
        ForeignKey("newspapers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    newspaper: Mapped["Newspaper"] = relationship(back_populates="editions")
