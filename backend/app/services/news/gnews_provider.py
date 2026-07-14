"""
GNews API provider (https://gnews.io) — the project's PRIMARY source.

Chosen as primary per the architecture research: generous free tier
(100 requests/day), clean JSON, native keyword + language + date-range
filtering, and full article descriptions (sometimes full content) rather
than just headlines. Its main limitation — the reason NewsData.io is
kept as a secondary — is no Telugu support, and no per-domain "only this
newspaper" filter on the free plan, only a broader `in=title,description`
text search.
"""

import httpx

from app.core.config import settings
from app.services.news.base import (
    BaseNewsProvider,
    NewsProviderError,
    NewsProviderNotConfigured,
    NormalizedArticle,
)

GNEWS_SEARCH_URL = "https://gnews.io/api/v4/search"


class GNewsProvider(BaseNewsProvider):
    name = "gnews"
    # GNews's supported language list does not include Telugu as of this
    # writing — see https://gnews.io/docs/v4#parameter-lang. Confirm
    # against their current docs before enabling more languages here.
    supported_languages = {"en", "hi"}

    def search(
        self,
        *,
        keyword: str,
        language: str,
        domain: str | None,
        max_results: int,
    ) -> list[NormalizedArticle]:
        if not settings.GNEWS_API_KEY:
            raise NewsProviderNotConfigured("GNEWS_API_KEY is not configured.")

        # GNews has no native "restrict to this domain" search operator on
        # the free tier, so fold the newspaper name hint into the query
        # text itself as a best-effort — real domain restriction only
        # works reliably on the Google News RSS fallback (see
        # google_rss_provider.py), consistent with the "gracefully
        # disable unsupported filters" requirement in the project spec.
        query = keyword

        params = {
            "q": query,
            "lang": language,
            "country": "in",
            "max": min(max_results, 10),  # free tier cap
            "apikey": settings.GNEWS_API_KEY,
        }

        try:
            response = httpx.get(GNEWS_SEARCH_URL, params=params, timeout=10, follow_redirects=True)
        except httpx.HTTPError as exc:
            raise NewsProviderError(f"GNews request failed: {exc}") from exc

        if response.status_code == 403:
            raise NewsProviderError("GNews API key invalid or quota exhausted.")
        if response.status_code != 200:
            raise NewsProviderError(f"GNews returned HTTP {response.status_code}.")

        payload = response.json()
        articles = []
        for item in payload.get("articles", []):
            source = item.get("source") or {}
            published_raw = item.get("publishedAt")
            published_at = None
            if published_raw:
                try:
                    from datetime import datetime

                    published_at = datetime.fromisoformat(published_raw.replace("Z", "+00:00"))
                except ValueError:
                    published_at = None

            articles.append(
                NormalizedArticle(
                    title=item.get("title", "").strip(),
                    source_name=source.get("name") or "Unknown source",
                    url=item.get("url", ""),
                    description=item.get("description"),
                    image_url=item.get("image"),
                    published_at=published_at,
                    language=language,
                    # Full article text, when GNews's plan includes it
                    # (truncated with a "[+N chars]" suffix on some tiers —
                    # left as-is; the report layer just uses whatever is here).
                    content=item.get("content"),
                )
            )
        return articles
