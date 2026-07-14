"""
Database engine and session setup using SQLAlchemy.

NOTE (Day 1): This module is created so the project structure is complete
and future modules can import `get_db` directly. No routes use this yet —
today's /health endpoint deliberately does NOT touch the database, to
keep the "backend is running" proof independent of MySQL being configured.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

connect_args = {"ssl": {"ssl_mode": "REQUIRED"}} if settings.APP_ENV == "production" else {}
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
