"""
Application configuration.

All settings are read from environment variables (via .env in development).
Nothing is hardcoded here so the same code runs in dev / staging / prod
by just swapping the .env file.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- General ---
    APP_NAME: str = "NewsPulse API"
    APP_ENV: str = "development"
    API_V1_PREFIX: str = "/api/v1"

    # --- CORS ---
    # The React dev server (Vite) runs on 5173 by default.
    FRONTEND_ORIGIN: str = "http://localhost:5173"

    # --- Database (MySQL) ---
    # Not yet used to run queries on Day 1 — reserved for when
    # models/CRUD are implemented.
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = "changeme"
    DB_NAME: str = "newspulse"

    # --- Auth ---
    SECRET_KEY: str = "changeme-in-env"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    # Used instead of ACCESS_TOKEN_EXPIRE_MINUTES when the user checks
    # "Keep me signed in" on the login form.
    REMEMBER_ME_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # --- Outbound email (forgot-password) ---
    # If SMTP_HOST is left blank, the app falls back to logging the reset
    # link to the console instead of emailing it — so registration/login/
    # forgot-password all still work out of the box with zero mail setup.
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True
    SMTP_FROM_EMAIL: str = "no-reply@newspulse.local"
    SMTP_FROM_NAME: str = "NewsPulse"

    @property
    def SMTP_CONFIGURED(self) -> bool:
        return bool(self.SMTP_HOST and self.SMTP_USER and self.SMTP_PASSWORD)

    # --- News providers ---
    # Primary: GNews (https://gnews.io) — free tier, sign up for a key.
    # Secondary: NewsData.io (https://newsdata.io) — free tier, sign up for a key.
    # Fallback: Google News RSS — no key needed, always active.
    # Leave either key blank to skip straight past that provider.
    GNEWS_API_KEY: str = ""
    NEWSDATA_API_KEY: str = ""

    # --- Report generation ---
    # Where generated PDFs are written, relative to the backend/ folder
    # unless given as an absolute path. Created automatically on startup.
    REPORTS_DIR: str = "generated_reports"

    # --- Search result caching ---
    # How long a cached search's results stay "fresh enough" to serve
    # without hitting the news provider again. Short enough that a
    # search still reflects genuinely recent news, long enough to
    # meaningfully cut down on free-tier API usage for repeated/popular
    # searches (e.g. multiple users searching "steel" the same morning).
    SEARCH_CACHE_FRESHNESS_HOURS: int = 3

    # --- Article retention (cleanup cron) ---
    # Cached articles older than this are deleted by the cleanup job
    # (see app/scripts/cleanup_old_articles.py) — keeps the database from
    # growing unbounded. Articles attached to a still-existing report are
    # never deleted regardless of age (see that script for why).
    ARTICLE_RETENTION_DAYS: int = 90

    @property
    def DATABASE_URL(self) -> str:
        # Username/password are URL-encoded because MySQL passwords often
        # contain characters like @, :, or / that would otherwise be
        # misread as part of the URL's own structure (e.g. an @ in the
        # password getting confused with the @ that separates credentials
        # from the host).
        from urllib.parse import quote_plus

        user = quote_plus(self.DB_USER)
        password = quote_plus(self.DB_PASSWORD)
        return f"mysql+pymysql://{user}:{password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
