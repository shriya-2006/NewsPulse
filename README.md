# NewsPulse — Enterprise News Monitoring & Report Generation System

**Internship project — RINL, Visakhapatnam Steel Plant**

Automates the daily manual process of searching news sites for
industry-relevant coverage (Steel, Coal, Iron Ore, Manufacturing, RINL,
Government Policies, Mining, Exports) and compiling it into a PDF report
for the Director.

---

## Recent fixes

A round of fixes on top of the five core modules, based on real usage:

1. **Removed the "Backend Connected Successfully" status chip** from the
   Dashboard — it was a Day-1 development aid, not meant to ship.
2. **Tags are now multi-select.** Clicking multiple tags searches for
   any of them (combined with `OR`) instead of replacing the previous
   selection.
3. **Custom date filter is now a range** (`date_from` / `date_to`)
   instead of a single date.
4. **Added Telugu and Hindi predefined tags** — all 23 industry tags
   now have Telugu and Hindi versions, shown automatically based on the
   selected search language (`GET /news/tags?language=te`).
5. **The Language → Newspaper → Edition filter is now a genuine
   database-backed cascade**, not a static list. Newspapers and
   editions live in real tables (`newspapers`, `newspaper_editions` —
   see backend/README.md), seeded automatically on first startup.
   Selecting a language fetches that language's newspapers
   (`GET /news/newspapers?language=Telugu` — accepts either the code or
   the display name); selecting a newspaper fetches its editions
   (`GET /news/editions?newspaper=eenadu`); changing the language resets
   the newspaper and edition, changing the newspaper resets the
   edition; a newspaper with no editions on file shows "No editions
   available." rather than an error. **Adding a new newspaper or
   edition is a database `INSERT` — no frontend or backend code changes,
   no redeploy.**
6. **Report PDFs use real article text when the news provider supplies
   it** (GNews/NewsData.io on paid plans populate a `content` field;
   the RSS fallback never does). Without that, the PDF falls back to
   the search result's `description`, then to a "no summary available"
   note. No web scraping of the original article page is done — if you
   want fuller content in reports, the way to get it is real GNews/
   NewsData.io API keys (see backend/README.md), not scraping.
7. **Newspaper filtering is now strictly enforced, not just hinted.**
   A real bug was found: selecting a newspaper alongside multiple tags
   (`Steel OR RINL`) silently broke the filter, because
   `Steel OR RINL site:thehindu.com` was being parsed as
   `Steel OR (RINL site:thehindu.com)` — the site restriction only
   applied to half the query. Fixed by always parenthesizing the
   keyword expression, plus every result is now verified after
   fetching (by URL domain or source name, whichever is reliable for
   that provider) — so a newspaper filter genuinely means "only this
   outlet's articles," with the aggregator falling back to the next
   provider if the strict check leaves nothing.
8. **Edition no longer requires a newspaper to be selected first** —
   picking just an edition (e.g. "Visakhapatnam") now searches every
   newspaper for that location, via a new `GET /news/editions` (no
   `newspaper` param) that returns the deduplicated union of every
   edition across all 12 newspapers.
9. **Report PDFs now show more of each article's available text.**
   GNews/NewsData.io's `content` field is often truncated (cut off with
   a `[+N chars]` marker, which is now stripped); when `description`
   adds genuinely different information, both are kept in the report
   instead of picking just one. Still no scraping — this only makes
   better use of what the provider already returns.
10. **Fixed a real bug causing Telugu (and any) searches to sometimes
    return nothing: a single tag click was firing the search request
    multiple times.** The tag-toggle handler called `performSearch`
    (a network request) from inside the function passed to
    `setSelectedTags` — React is explicitly allowed to invoke that
    function more than once per update (and does, on purpose, under
    `React.StrictMode` in development, specifically to catch bugs like
    this one), so every click could fire 2+ identical searches, with
    each additional tag click re-firing the *entire* accumulated
    OR-query on top of that. Hammering Google News RSS this fast is a
    very plausible way to trip silent rate limiting (a `200 OK` with an
    empty feed, no explicit error) — which looks exactly like "no
    results," especially for Telugu/Hindi where the multi-tag flow
    naturally builds longer OR chains. Fixed by moving the search
    trigger out of the state updater into the handler body. Also added:
    a real distinction between "provider ran fine, found nothing" and
    "provider actually failed" (bad response, network error) — a search
    that comes back empty because a source genuinely broke now says so
    in the response's `notice` field, instead of showing the same
    generic message as an honest empty result.
11. **Fixed a second real bug the new diagnostic notice (from #10)
    immediately surfaced: Google News RSS requests weren't following
    redirects.** `httpx` (unlike Python's older, more common `requests`
    library) does not follow HTTP redirects by default. Google News RSS
    has been observed responding with a `302`, which — without
    `follow_redirects=True` — was being treated as an outright provider
    failure instead of being followed to the real feed content. All
    three news provider HTTP calls now set `follow_redirects=True`.

### About "NewsData.io API key invalid"

If your app's diagnostic notice mentions this, it means NewsData.io's
own server rejected the key with an HTTP 401 — the code sends it
correctly (as the `apikey` query parameter, matching their documented
API), so this isn't a code bug. It typically means one of: the key was
copied with extra whitespace/a line break, the key was regenerated or
revoked in the NewsData.io dashboard since it was first set, or (common
on their free tier) the account needs email verification before the
key activates. Worth double-checking directly in your NewsData.io
dashboard. This is harmless either way for search results — GNews and
the no-key RSS fallback still work independently of it.

12. **Fixed a third real bug: NewsData.io's `domain` filter param
    caused a 422 for certain newspapers (observed with Andhra Jyothy)
    while working for others, taking down the whole newspaper-filtered
    search instead of falling through to the RSS fallback.** In
    practice, NewsData.io's `domain` parameter appears to only accept
    domains from their own internal registered-source list, rejecting
    anything else outright — not the "silently ignored on the free
    tier" behavior originally assumed. Fixed by no longer sending
    `domain` to NewsData.io at all; newspaper filtering for this
    provider now relies entirely on the aggregator's own post-fetch
    verification (`_matches_newspaper`), the same approach already used
    for GNews, which never had a working domain filter to begin with.
13. **Added search result caching + a retention cleanup job**, per a
    direct suggestion from the project's guide: rather than calling a
    live news provider on every single search, results are now cached
    in the database and served from there for repeated/popular queries
    within a configurable freshness window — meaningful protection
    against free-tier API quota exhaustion (GNews: 100 requests/day,
    NewsData.io: 200/day) and reduces load on the RSS fallback, which
    is the endpoint most prone to rate limiting under heavy request
    volume. A companion cleanup job deletes cached articles/searches
    older than a configurable retention period (default 90 days),
    while permanently protecting any article that's ever been selected
    into a still-existing report, regardless of age. See
    backend/README.md's "Search result caching" and "Cleanup (the
    retention cron)" sections for the full design and how to schedule
    the cleanup job for real ongoing use.
14. **Fixed a real MySQL startup crash (error 3780) surfaced by adding
    the caching feature above: every table's ID/foreign-key columns
    now correctly compile to `BIGINT UNSIGNED` on MySQL, matching
    `database/schema.sql` exactly.** The ORM's shared ID type
    previously compiled to plain signed `BIGINT` on MySQL — invisible
    for a long time because every existing table had originally been
    created by running `schema.sql` directly (consistently UNSIGNED on
    both sides), only becoming a real, reproducible crash the moment a
    brand-new ORM-only table needed to reference an existing one, since
    MySQL 8.0.19+ rejects a foreign key whose referencing and
    referenced columns disagree on signedness. See backend/README.md's
    "If you hit MySQL error 3780" section if you're upgrading from a
    build before this fix.

---

## Architecture

```
┌──────────────────┐        REST / JSON        ┌───────────────────┐        SQL        ┌──────────┐
│  React Frontend    │ ─────────────────────────▶ │  FastAPI Backend    │ ─────────────────▶ │  MySQL    │
│  (Vite, React       │ ◀───────────────────────── │  routes → schemas   │ ◀───────────────── │  Database │
│   Router)            │                             │  → models            │                    │           │
└──────────────────┘                              └───────────────────┘                    └──────────┘
```

- **Frontend**: React (Vite), component-based, React Router for navigation
  between auth pages and the dashboard.
- **Backend**: FastAPI, layered into `routes` (HTTP handling) →
  `schemas` (Pydantic validation) → `models` (SQLAlchemy ORM), so each
  future feature slots into the same three folders.
- **Database**: MySQL. Full schema designed for the entire feature set
  (users, password resets, search history, reports, articles) — see
  `database/schema.sql`.

## Repository layout

```
newspulse/
├── backend/         # FastAPI app — see backend/README.md
├── frontend/        # React app — see frontend/README.md
└── database/
    └── schema.sql   # Full MySQL schema (all tables, Day 1 design)
```

## Status

| Deliverable                                   | Status |
|------------------------------------------------|--------|
| Architecture finalized                          | ✅ Done |
| Folder structure (frontend + backend)          | ✅ Done |
| React project setup                             | ✅ Done |
| FastAPI backend setup                           | ✅ Done |
| MySQL schema design                             | ✅ Done |
| Login / Register / Forgot Password UI          | ✅ Done |
| Dashboard UI shell (search, filters, reserved results area) | ✅ Done |
| `/api/v1/health` endpoint                       | ✅ Done |
| Frontend ↔ backend connection proof             | ✅ Done — live status chip on Dashboard |
| **Module 2 — JWT auth (register/login/forgot/reset/me/logout)** | ✅ Done |
| **Password hashing (bcrypt), protected routes, "remember me"** | ✅ Done |
| **Real forgot-password emails via SMTP, with console fallback** | ✅ Done |
| **Dashboard is a protected route; real sign-out** | ✅ Done |
| **Module 3 — News search (GNews → NewsData.io → Google News RSS fallback)** | ✅ Done |
| **Predefined + custom tags, newspaper/edition/date filters** | ✅ Done |
| **Article selection, loading skeletons, error/no-results states, pagination** | ✅ Done |
| **Module 4 — PDF report generation (WeasyPrint, cover page, headers/footers/page numbers)** | ✅ Done |
| **Report + article storage in MySQL, authenticated PDF download** | ✅ Done |
| **Module 5 — Admin dashboard (stats, 6 charts, recent activity, per-user activity)** | ✅ Done |
| **Report History page (`/reports`) — list + re-download past reports** | ✅ Done |
| **Automated backend test suite (76 pytest tests)** | ✅ Done |

Every major feature area from the original project spec — auth, search, report generation, and admin analytics — is now built end-to-end.

## Running both services

```bash
# Terminal 1 — backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # set a real SECRET_KEY and your MySQL credentials
uvicorn app.main:app --reload

# Terminal 2 — frontend
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open http://localhost:5173 — register an account, search "steel", select
a couple of articles, and click "Generate Report" to download a real PDF.
Promote yourself to admin (see backend/README.md) to see the Admin Dashboard.

## What's left (polish, not new features)

The core spec is fully implemented. What would remain for a genuine
production deployment:

1. Real SMTP credentials configured for forgot-password (currently
   falls back to console logging if unset).
2. Real GNews/NewsData.io API keys for richer results than the RSS
   fallback alone (full article text, images).
3. Deployment hardening: HTTPS, a production MySQL instance, moving
   `SECRET_KEY`/API keys out of `.env` into a real secrets manager,
   and switching `Base.metadata.create_all()` to proper Alembic
   migrations. Containerizing this (Docker/docker-compose) is a
   natural next step whenever you're ready for it.

