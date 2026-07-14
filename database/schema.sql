-- ============================================================================
-- NewsPulse — Database Schema (Day 1 Design)
-- ============================================================================
-- Designed now, implemented later. Reflects the full Day-1-through-final
-- feature set (auth, search history, reports, admin analytics) even though
-- only the health endpoint is wired to code today.
-- ============================================================================

CREATE DATABASE IF NOT EXISTS newspulse
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE newspulse;

-- ----------------------------------------------------------------------------
-- USERS
-- Stores registered employees. Supports login, registration, forgot-password,
-- and the is_admin flag drives access to the admin dashboard.
-- ----------------------------------------------------------------------------
CREATE TABLE users (
    id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    full_name           VARCHAR(150)        NOT NULL,
    email               VARCHAR(255)        NOT NULL UNIQUE,
    password_hash       VARCHAR(255)        NOT NULL,
    is_admin            BOOLEAN             NOT NULL DEFAULT FALSE,
    is_active           BOOLEAN             NOT NULL DEFAULT TRUE,
    last_login_at       DATETIME            NULL,
    created_at          DATETIME            NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME            NOT NULL DEFAULT CURRENT_TIMESTAMP
                                             ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- PASSWORD_RESET_TOKENS
-- Backs the "Forgot Password" flow: a short-lived token emailed to the user.
-- ----------------------------------------------------------------------------
CREATE TABLE password_reset_tokens (
    id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id             BIGINT UNSIGNED     NOT NULL,
    token               VARCHAR(255)        NOT NULL UNIQUE,
    expires_at          DATETIME            NOT NULL,
    used                BOOLEAN             NOT NULL DEFAULT FALSE,
    created_at          DATETIME            NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_reset_token_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- NEWSPAPERS / NEWSPAPER_EDITIONS
-- The Language -> Newspaper -> Edition hierarchy, stored here instead of
-- hardcoded in the frontend or backend code — adding a new newspaper or
-- edition is a plain INSERT, with no frontend/backend changes needed.
-- The backend auto-seeds these from app/db/seed_data.py on first startup
-- if empty, so a fresh install doesn't strictly need the INSERTs below —
-- they're included for completeness/reference.
-- ----------------------------------------------------------------------------
CREATE TABLE newspapers (
    id                      BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `key`                   VARCHAR(100)        NOT NULL UNIQUE,
    label                   VARCHAR(150)        NOT NULL,
    language                ENUM('en', 'te', 'hi') NOT NULL,
    domain                  VARCHAR(255)        NOT NULL,
    edition_query_supported BOOLEAN             NOT NULL DEFAULT FALSE,
    INDEX idx_newspaper_language (language)
) ENGINE=InnoDB;

CREATE TABLE newspaper_editions (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    newspaper_id    BIGINT UNSIGNED     NOT NULL,
    name            VARCHAR(100)        NOT NULL,
    CONSTRAINT fk_edition_newspaper
        FOREIGN KEY (newspaper_id) REFERENCES newspapers(id) ON DELETE CASCADE,
    CONSTRAINT uq_newspaper_edition_name UNIQUE (newspaper_id, name)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- SEARCH_HISTORY
-- One row per search a user performs (keyword + filters used). Powers both
-- the user's own history and the admin dashboard's "total searches" metric.
-- ----------------------------------------------------------------------------
CREATE TABLE search_history (
    id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id             BIGINT UNSIGNED     NOT NULL,
    keyword             VARCHAR(255)        NOT NULL,
    language             ENUM('en', 'te', 'hi') NOT NULL DEFAULT 'en',
    newspaper            VARCHAR(100)        NULL,
    edition              VARCHAR(100)        NULL,
    result_count         INT UNSIGNED        NOT NULL DEFAULT 0,
    searched_at          DATETIME            NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_search_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_search_user (user_id),
    INDEX idx_search_keyword (keyword)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- CUSTOM_TAGS
-- Per-user search tags added on top of the shared predefined tag list
-- (which lives in code — app/utils/newspaper_sources.py — not a table,
-- since every user sees the same predefined set).
-- ----------------------------------------------------------------------------
CREATE TABLE custom_tags (
    id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id             BIGINT UNSIGNED     NOT NULL,
    tag                 VARCHAR(100)        NOT NULL,
    created_at          DATETIME            NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_custom_tag_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT uq_custom_tag_user_tag UNIQUE (user_id, tag)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- REPORTS
-- One row per generated PDF report. keyword/language/newspaper/edition
-- capture the search context so the PDF cover page (and any future
-- regeneration/audit) can show what the report was actually built from.
-- ----------------------------------------------------------------------------
CREATE TABLE reports (
    id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id             BIGINT UNSIGNED     NOT NULL,
    title               VARCHAR(255)        NOT NULL,
    keyword             VARCHAR(255)        NOT NULL,
    language             ENUM('en', 'te', 'hi') NOT NULL DEFAULT 'en',
    newspaper            VARCHAR(100)        NULL,
    edition              VARCHAR(100)        NULL,
    file_path            VARCHAR(500)        NOT NULL,
    article_count         INT UNSIGNED        NOT NULL DEFAULT 0,
    generated_at          DATETIME            NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_report_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_report_user (user_id)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- ARTICLES
-- Cached copy of a news article that was selected into at least one report,
-- so a report can be regenerated/audited without re-fetching from the
-- external news source. `content` holds the complete article text when the
-- provider supplied it (GNews/NewsData.io on paid plans; otherwise NULL) —
-- the report falls back to `description` + `url` when it's missing.
-- ----------------------------------------------------------------------------
CREATE TABLE articles (
    id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    source_name          VARCHAR(255)        NOT NULL,
    title                VARCHAR(500)        NOT NULL,
    url                  VARCHAR(1000)       NOT NULL,
    description          TEXT                NULL,
    image_url             VARCHAR(1000)       NULL,
    content               LONGTEXT            NULL,
    language              ENUM('en', 'te', 'hi') NOT NULL DEFAULT 'en',
    published_at          DATETIME            NULL,
    fetched_at            DATETIME            NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_article_url (url(500))
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- REPORT_ARTICLES  (many-to-many: a report contains many articles,
-- an article can appear in many reports)
-- ----------------------------------------------------------------------------
CREATE TABLE report_articles (
    report_id            BIGINT UNSIGNED     NOT NULL,
    article_id            BIGINT UNSIGNED     NOT NULL,
    PRIMARY KEY (report_id, article_id),
    CONSTRAINT fk_ra_report
        FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE,
    CONSTRAINT fk_ra_article
        FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- CACHED_SEARCHES / CACHED_SEARCH_ARTICLES
-- Caches a search's full result set so a repeat of the exact same query
-- (same keyword/language/newspaper/edition/date range) can be served
-- from the database instead of calling a live news provider again —
-- meaningful on free-tier API keys (GNews: 100 req/day, NewsData.io:
-- 200 req/day) and reduces load on the Google News RSS fallback.
-- `cache_key` is a normalized fingerprint of the query (see
-- app/services/search_cache_service.py); `fetched_at` is checked
-- against SEARCH_CACHE_FRESHNESS_HOURS to decide whether a cache hit
-- is still fresh enough to serve. Rows older than ARTICLE_RETENTION_DAYS
-- are deleted by the cleanup job (app/scripts/cleanup_old_articles.py),
-- which is meant to run on a schedule (see that script's docstring for
-- how to wire it into cron / Task Scheduler / a host's Cron Job feature).
-- ----------------------------------------------------------------------------
CREATE TABLE cached_searches (
    id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    cache_key           VARCHAR(64)         NOT NULL UNIQUE,
    keyword             VARCHAR(255)        NOT NULL,
    language             ENUM('en', 'te', 'hi') NOT NULL,
    newspaper            VARCHAR(100)        NULL,
    edition              VARCHAR(100)        NULL,
    date_filter          VARCHAR(20)         NOT NULL,
    provider_used         VARCHAR(20)         NULL,
    result_count          INT UNSIGNED        NOT NULL DEFAULT 0,
    fetched_at            DATETIME            NOT NULL,
    INDEX idx_cached_search_key (cache_key)
) ENGINE=InnoDB;

CREATE TABLE cached_search_articles (
    cached_search_id     BIGINT UNSIGNED     NOT NULL,
    article_id            BIGINT UNSIGNED     NOT NULL,
    position              INT UNSIGNED        NOT NULL DEFAULT 0,
    PRIMARY KEY (cached_search_id, article_id),
    CONSTRAINT fk_csa_search
        FOREIGN KEY (cached_search_id) REFERENCES cached_searches(id) ON DELETE CASCADE,
    CONSTRAINT fk_csa_article
        FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================================================
-- Notes for future days:
--   - is_admin on `users` gates access to admin-only endpoints/UI.
--   - Admin dashboard metrics (total searches, reports generated) are
--     simple COUNT()/GROUP BY queries over search_history / reports —
--     no separate analytics table needed at this scale.
-- ============================================================================
