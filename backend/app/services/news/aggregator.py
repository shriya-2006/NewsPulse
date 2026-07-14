"""
Tries providers in the architecture's specified order — GNews (primary) →
NewsData.io (secondary) → Google News RSS (fallback) — and returns the
first one that actually produces results. Also applies date-range
filtering, and — when a specific newspaper was requested — a strict
post-fetch check that the article genuinely came from that outlet,
since not every provider supports it natively in a way that's worth
branching on per-provider.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from urllib.parse import urlparse

from app.services.news.base import NewsProviderError, NewsProviderNotConfigured, NormalizedArticle
from app.services.news.gnews_provider import GNewsProvider
from app.services.news.google_rss_provider import GoogleNewsRSSProvider
from app.services.news.newsdata_provider import NewsDataProvider

# Order matters — this IS the "primary / secondary / fallback" architecture.
_PROVIDERS = [GNewsProvider(), NewsDataProvider(), GoogleNewsRSSProvider()]


@dataclass
class SearchOutcome:
    articles: list[NormalizedArticle]
    provider_used: str | None
    provider_errors: dict[str, str]  # provider name -> why it was skipped/failed
    # Subset of provider_errors' keys that represent a genuine failure
    # (the provider actually tried and broke — bad response, network
    # error, rate limit) rather than a routine/expected skip (no API key,
    # unsupported language, or simply no matching articles). Lets callers
    # surface real problems without parsing error message text to guess
    # which is which.
    real_failures: set[str]


def _date_bounds(
    date_filter: str, date_from: date | None, date_to: date | None
) -> tuple[datetime | None, datetime | None]:
    """Returns (start, end) as UTC datetimes, or (None, None) for 'any'.

    `end` is exclusive — e.g. a date_to of July 4th includes all of July
    4th, up to (but not including) midnight July 5th.
    """
    if date_filter == "today":
        start = datetime.combine(date.today(), time.min, tzinfo=timezone.utc)
        return start, start + timedelta(days=1)
    if date_filter == "yesterday":
        start = datetime.combine(date.today() - timedelta(days=1), time.min, tzinfo=timezone.utc)
        return start, start + timedelta(days=1)
    if date_filter == "custom" and date_from and date_to:
        start = datetime.combine(date_from, time.min, tzinfo=timezone.utc)
        end = datetime.combine(date_to, time.min, tzinfo=timezone.utc) + timedelta(days=1)
        return start, end
    return None, None


def _within_range(article: NormalizedArticle, start: datetime | None, end: datetime | None) -> bool:
    if start is None:
        return True
    if article.published_at is None:
        # Can't verify the date (some feeds omit it) — keep it rather than
        # silently dropping potentially-relevant results.
        return True
    published = article.published_at
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)
    return start <= published < end


def _strip_www(host: str) -> str:
    return host[4:] if host.startswith("www.") else host


def _matches_newspaper(article: NormalizedArticle, domain: str, label: str) -> bool:
    """
    True if this article genuinely appears to come from the requested
    newspaper. Checks two independent signals because no single one is
    reliable across all three providers:

    - URL domain: works for GNews/NewsData.io, which link directly to
      the original publisher.
    - source_name vs. the newspaper's label: the only reliable signal
      for Google News RSS, whose <link> is always a news.google.com
      redirect wrapper, never the publisher's own domain — so domain
      matching alone would incorrectly reject every real RSS result.
    """
    netloc = _strip_www(urlparse(article.url).netloc.lower())
    domain_clean = _strip_www(domain.lower())
    if domain_clean and (domain_clean in netloc or netloc in domain_clean):
        return True
    return article.source_name.strip().lower() == label.strip().lower()


def search_news(
    *,
    keyword: str,
    language: str,
    domain: str | None,
    newspaper_label: str | None,
    date_filter: str,
    date_from: date | None,
    date_to: date | None,
    max_results: int,
) -> SearchOutcome:
    start, end = _date_bounds(date_filter, date_from, date_to)
    errors: dict[str, str] = {}
    real_failures: set[str] = set()

    for provider in _PROVIDERS:
        if not provider.supports_language(language):
            errors[provider.name] = f"Does not support language '{language}'."
            continue

        try:
            # Fetch a bit more than requested since the date filter below
            # is applied client-side and may remove some results.
            raw_articles = provider.search(
                keyword=keyword,
                language=language,
                domain=domain,
                max_results=max(max_results * 2, 20),
            )
        except NewsProviderNotConfigured as exc:
            # Routine and expected (no API key set) — not a real failure.
            errors[provider.name] = str(exc)
            continue
        except NewsProviderError as exc:
            errors[provider.name] = str(exc)
            real_failures.add(provider.name)
            continue

        filtered = [a for a in raw_articles if _within_range(a, start, end)]

        if domain and newspaper_label:
            filtered = [a for a in filtered if _matches_newspaper(a, domain, newspaper_label)]

        if filtered:
            return SearchOutcome(
                articles=filtered[:max_results],
                provider_used=provider.name,
                provider_errors=errors,
                real_failures=real_failures,
            )

        # Provider worked but had nothing (post date/newspaper filter) —
        # note it and keep trying the next provider rather than stopping here.
        errors[provider.name] = "No matching results."

    return SearchOutcome(articles=[], provider_used=None, provider_errors=errors, real_failures=real_failures)
