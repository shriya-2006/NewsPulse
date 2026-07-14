"""
User & password-reset ORM models.

Mirrors the `users` and `password_reset_tokens` tables from
database/schema.sql exactly — same columns, same defaults, same
foreign key — so the ORM and the hand-written schema never drift apart.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

# MySQL (production) uses BIGINT UNSIGNED AUTO_INCREMENT — see database/schema.sql.
# SQLite (only ever used for quick local unit tests) only auto-increments a
# column declared as plain INTEGER, so this variant keeps both working
# without any behavior change on MySQL.
#
# IMPORTANT: this must actually specify `unsigned=True` for the MySQL
# dialect, not just "BigInteger" — MySQL 8.0.19+ rejects creating a
# foreign key whose referencing column's signedness doesn't match the
# referenced column's (error 3780). Every existing table in a database
# set up by running database/schema.sql directly is already BIGINT
# UNSIGNED; a bare (signed) BigInteger here would only go unnoticed for
# as long as SQLAlchemy's create_all() never has to create a brand new
# table referencing one of those columns — which is exactly what
# surfaced this as a real, reproducible bug the first time a new
# ORM-only table (cached_search_articles) was added after the database
# already existed.
BigIntPK = mysql.BIGINT(unsigned=True).with_variant(Integer, "sqlite")

# Same underlying type, used on the *referencing* side of a foreign key
# (e.g. `user_id` on a child table) — kept as a separate, identically-named
# alias purely for readability at each call site (a column named
# `BigIntPK` on a non-primary-key column would read oddly), not because
# the type itself needs to differ from BigIntPK in any way.
BigIntFK = BigIntPK


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    reset_tokens: Mapped[list["PasswordResetToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigIntFK, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="reset_tokens")
