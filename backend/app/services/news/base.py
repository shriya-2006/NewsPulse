"""
Provider-agnostic contract every news source implements.

Why an interface at all: the project spec requires GNews as primary,
NewsData.io as secondary, and Google News RSS as a no-key fallback,
with automatic fallover when one is unavailable/unconfigured/rate-limited.
Routes and the aggregator only ever talk to this interface, so adding a
fourth provider later (NewsAPI.org, MediaStack, NewsCatcher) means
writing one new class — nothing else in the codebase changes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


class NewsProviderError(Exception):
    """
    Raised by a provider when it cannot fulfil a search — missing API key,
    network failure, rate limit, unsupported language, etc. The aggregator
    catches this and moves on to the next provider in the chain.
    """


class NewsProviderNotConfigured(NewsProviderError):
    """
    Raised specifically when a provider has no API key set. This is a
    routine, expected condition (GNews/NewsData.io are both optional —
    the app works via the RSS fallback with zero keys), not a genuine
    failure — kept as its own type so callers can tell "this source
    isn't set up" apart from "this source broke while actually trying"
    (rate limited, network error, malformed response, etc.) without
    parsing error message text to guess which is which.
    """


@dataclass
class NormalizedArticle:
    """
    The common shape every provider's response gets converted into
    before it reaches the frontend. Field names match `ArticleOut` in
    app/schemas/news.py one-for-one.
    """

    title: str
    source_name: str
    url: str
    description: str | None
    image_url: str | None
    published_at: datetime | None
    language: str
    # Complete article text, when the provider actually supplies it
    # (GNews/NewsData.io on paid plans). None on the free tier and
    # always None from the RSS fallback, which only ever gives a
    # snippet — report generation falls back to description + url
    # whenever this is missing, per the project spec.
    content: str | None = None


class BaseNewsProvider(ABC):
    #: Short identifier surfaced in the API response's `provider_used` field
    #: and used in log messages — e.g. "gnews", "newsdata", "google_rss".
    name: str

    #: Languages this provider's API actually supports. The aggregator
    #: skips straight to the next provider for an unsupported language
    #: instead of making a doomed API call.
    supported_languages: set[str] = {"en"}

    def supports_language(self, language: str) -> bool:
        return language in self.supported_languages

    @abstractmethod
    def search(
        self,
        *,
        keyword: str,
        language: str,
        domain: str | None,
        max_results: int,
    ) -> list[NormalizedArticle]:
        """
        Returns normalized articles for `keyword`, optionally restricted
        to `domain` (a newspaper's website, e.g. "thehindu.com") when the
        person picked a specific newspaper filter and this provider can
        act on it. Must raise NewsProviderError rather than returning an
        empty list on failure, so the aggregator can tell "no results"
        apart from "this provider didn't work" and try the next one.
        """
        raise NotImplementedError
