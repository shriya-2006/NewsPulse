"""
NewsPulse API — application entrypoint.

Run with:
    uvicorn app.main:app --reload
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import admin, auth, health, news, reports
from app.core.config import settings
from app.db.database import Base, SessionLocal, engine
from app.services import newspaper_service

# Importing app.models registers every ORM model on Base.metadata so
# create_all() below knows about all of them.
from app import models  # noqa: F401

app = FastAPI(
    title=settings.APP_NAME,
    description="Enterprise News Monitoring & Report Generation System — API",
    version="0.5.0",
)

# Allow the React dev server to call this API during local development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    # Dev convenience: creates any tables that don't exist yet without
    # touching ones that do. The canonical schema is still database/schema.sql —
    # this just keeps a fresh dev DB in sync with the ORM automatically.
    Base.metadata.create_all(bind=engine)

    # Populate the newspaper/edition hierarchy on first run — a complete
    # no-op on every subsequent startup once the table has any rows,
    # including newspapers added manually afterward.
    db = SessionLocal()
    try:
        newspaper_service.seed_if_empty(db)
    finally:
        db.close()

    # Make sure the folder generated PDFs get written to actually exists.
    reports_dir = Path(settings.REPORTS_DIR)
    if not reports_dir.is_absolute():
        reports_dir = Path(__file__).resolve().parent.parent / reports_dir
    reports_dir.mkdir(parents=True, exist_ok=True)


# --- Routers ---
# Every future feature gets its own router module under app/api/routes
# and is registered here with its own prefix.
app.include_router(health.router, prefix=settings.API_V1_PREFIX)
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(news.router, prefix=settings.API_V1_PREFIX)
app.include_router(reports.router, prefix=settings.API_V1_PREFIX)
app.include_router(admin.router, prefix=settings.API_V1_PREFIX)


@app.get("/")
def root():
    return {"message": "NewsPulse API is running. See /docs for API documentation."}

