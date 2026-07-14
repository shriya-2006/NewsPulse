"""
Shared pytest fixtures.

Every test gets a fresh in-memory SQLite database (StaticPool keeps one
connection alive for the whole test so tables don't vanish between
queries) — tests never touch a real MySQL instance, and never leak
state into each other.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.db.database as dbmod


@pytest.fixture()
def db_session_factory():
    """Creates a fresh schema in a fresh in-memory DB for one test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    dbmod.engine = engine
    dbmod.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    from app import models  # noqa: F401  (registers all models on Base.metadata)
    from app.db.database import Base

    Base.metadata.create_all(bind=engine)

    # Seed the newspaper/edition hierarchy the same way main.py does on
    # real startup, so tests see the same 12 newspapers without needing
    # their own copy of the seed data.
    from app.services.newspaper_service import seed_if_empty

    seed_session = dbmod.SessionLocal()
    try:
        seed_if_empty(seed_session)
    finally:
        seed_session.close()

    yield dbmod.SessionLocal


@pytest.fixture()
def client(db_session_factory, tmp_path, monkeypatch):
    """A TestClient wired to the fresh per-test database."""
    from app.core.config import settings

    # Reports write to a per-test temp directory instead of the real one.
    monkeypatch.setattr(settings, "REPORTS_DIR", str(tmp_path / "reports"))
    # No real news provider keys during tests — forces the RSS fallback
    # path unless a test explicitly sets a key to exercise GNews/NewsData.
    monkeypatch.setattr(settings, "GNEWS_API_KEY", "")
    monkeypatch.setattr(settings, "NEWSDATA_API_KEY", "")

    from fastapi.testclient import TestClient

    from app.db.database import get_db
    from app.main import app

    def override_get_db():
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def register_user(client):
    """Factory fixture: register_user(email=..., password=..., full_name=...) -> (token, headers)."""

    def _register(
        full_name: str = "Shriya Reddy",
        email: str = "shriya@vizagsteel.com",
        password: str = "Steel1234",
    ):
        response = client.post(
            "/api/v1/auth/register",
            json={"full_name": full_name, "email": email, "password": password},
        )
        assert response.status_code == 201, response.text
        token = response.json()["access_token"]
        return token, {"Authorization": f"Bearer {token}"}

    return _register


@pytest.fixture()
def admin_headers(client, register_user, db_session_factory):
    """Registers a user and promotes them to admin directly via the DB."""
    _, headers = register_user(email="admin@vizagsteel.com", full_name="Admin User")

    from app.models.user import User

    db = db_session_factory()
    user = db.query(User).filter(User.email == "admin@vizagsteel.com").first()
    user.is_admin = True
    db.commit()
    db.close()

    return headers


SAMPLE_RSS_FEED = b"""<?xml version="1.0"?><rss><channel>
<item>
  <title>Steel output rises - The Hindu</title>
  <link>https://example.com/article-1</link>
  <pubDate>Fri, 04 Jul 2026 06:30:00 GMT</pubDate>
  <description>Steel news snippet about production increases.</description>
  <source url="https://thehindu.com">The Hindu</source>
</item>
<item>
  <title>Second steel story - The Hindu</title>
  <link>https://example.com/article-2</link>
  <pubDate>Fri, 04 Jul 2026 05:00:00 GMT</pubDate>
  <description>Another snippet about the plant.</description>
  <source url="https://thehindu.com">The Hindu</source>
</item>
</channel></rss>"""


@pytest.fixture()
def mock_rss(monkeypatch):
    """Patches httpx.get so any news search resolves via a canned RSS feed."""
    import httpx

    class FakeResponse:
        status_code = 200
        content = SAMPLE_RSS_FEED

    monkeypatch.setattr(httpx, "get", lambda *a, **kw: FakeResponse())
    return SAMPLE_RSS_FEED
