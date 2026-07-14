"""
NewsData.io provider (https://newsdata.io) — the project's SECONDARY source.

Chosen as secondary specifically because it supports Telugu ('te') as a
native language filter, which GNews does not — so it's the first real
fallback whenever a Telugu search comes in, and a general fallback for
English/Hindi when GNews is unavailable or its quota is exhausted.
"""

from datetime import datetime

import httpx

from app.core.config import settings
from app.services.news.base import (
    BaseNewsProvider,
    NewsProviderError,
    NewsProviderNotConfigured,
    NormalizedArticle,
)

NEWSDATA_SEARCH_URL = "https://newsdata.io/api/1/news"


class NewsDataProvider(BaseNewsProvider):
    name = "newsdata"
    supported_languages = {"en", "te", "hi"}

    def search(
        self,
        *,
        keyword: str,
        language: str,
        domain: str | None,
        max_results: int,
    ) -> list[NormalizedArticle]:
        if not settings.NEWSDATA_API_KEY:
            raise NewsProviderNotConfigured("NEWSDATA_API_KEY is not configured.")

        params = {
            "apikey": settings.NEWSDATA_API_KEY,
            "q": keyword,
            "language": language,
            "country": "in",
        }
        # Deliberately NOT sending NewsData.io's `domain` param, even
        # though their docs mention it: in practice it appears to only
        # accept domains from their own internal registered-source list,
        # and 422s outright for domains it doesn't recognize (observed
        # with andhrajyothy.com, while other domains worked) — rather
        # than the "silently ignored on free tier" behavior originally
        # assumed here. Newspaper filtering for this provider relies
        # entirely on the aggregator's own post-fetch verification
        # (`_matches_newspaper` in aggregator.py), the same approach
        # already used for GNews, which never had a working domain
        # filter to begin with. This trades a bit of fetch efficiency
        # (broader initial results, narrowed after the fact) for not
        # depending on undocumented behavior of a third-party API.

        try:
            response = httpx.get(NEWSDATA_SEARCH_URL, params=params, timeout=10, follow_redirects=True)
        except httpx.HTTPError as exc:
            raise NewsProviderError(f"NewsData.io request failed: {exc}") from exc

        if response.status_code == 401:
            raise NewsProviderError("NewsData.io API key invalid.")
        if response.status_code == 429:
            raise NewsProviderError("NewsData.io rate limit exceeded.")
        if response.status_code != 200:
            raise NewsProviderError(f"NewsData.io returned HTTP {response.status_code}.")

        payload = response.json()
        if payload.get("status") != "success":
            raise NewsProviderError(payload.get("message", "NewsData.io returned an error."))

        articles = []
        for item in payload.get("results", []) or []:
            published_raw = item.get("pubDate")
            published_at = None
            if published_raw:
                try:
                    # NewsData.io returns "YYYY-MM-DD HH:MM:SS" (UTC, no offset).
                    published_at = datetime.strptime(published_raw, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    published_at = None

            articles.append(
                NormalizedArticle(
                    title=(item.get("title") or "").strip(),
                    source_name=item.get("source_id") or "Unknown source",
                    url=item.get("link", ""),
                    description=item.get("description"),
                    image_url=item.get("image_url"),
                    published_at=published_at,
                    language=language,
                    # "content": "ONLY AVAILABLE IN PAID PLANS" on the free
                    # tier — that literal placeholder string is filtered out
                    # so it never ends up looking like real article text.
                    content=(
                        item.get("content")
                        if item.get("content") and "ONLY AVAILABLE IN PAID PLANS" not in item.get("content", "")
                        else None
                    ),
                )
            )
        return articles
