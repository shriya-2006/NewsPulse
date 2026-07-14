"""
Google News RSS provider — the project's FALLBACK source.

No API key, no signup, no rate-limit surprises during a demo — this is
what makes search work the moment the backend is cloned, before anyone
has requested a GNews/NewsData.io key. It's also the only provider that
can reliably restrict results to one newspaper, via the `site:` search
operator baked into the query string, which is why domain filtering is
implemented here even though the interface supports it everywhere.

Trade-off (documented per the project's "normalize but note gaps"
requirement): no clean `source`/`description` separation the way a real
news API gives you — everything is scraped out of an RSS <item>, so
descriptions are short snippets, not full article text, and there's no
image field at all (Google's RSS feed doesn't include one).
"""

import html
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus
from xml.etree import ElementTree

import httpx

from app.services.news.base import BaseNewsProvider, NewsProviderError, NormalizedArticle

RSS_BASE_URL = "https://news.google.com/rss/search"

# hl (interface language) / ceid (country:language) per Google News' own
# locale scheme — see https://news.google.com/rss/search?q=x&hl=<hl>&ceid=<ceid>
_LOCALE_BY_LANGUAGE = {
    "en": {"hl": "en-IN", "gl": "IN", "ceid": "IN:en"},
    "hi": {"hl": "hi-IN", "gl": "IN", "ceid": "IN:hi"},
    "te": {"hl": "te-IN", "gl": "IN", "ceid": "IN:te"},
}


def _strip_html(text: str) -> str:
    """Google's RSS <description> is an HTML snippet — reduce it to a
    plain, single-spaced text preview."""
    without_tags = re.sub(r"<[^>]+>", " ", text or "")
    unescaped = html.unescape(without_tags)
    return re.sub(r"\s+", " ", unescaped).strip()


class GoogleNewsRSSProvider(BaseNewsProvider):
    name = "google_rss"
    supported_languages = {"en", "te", "hi"}

    def search(
        self,
        *,
        keyword: str,
        language: str,
        domain: str | None,
        max_results: int,
    ) -> list[NormalizedArticle]:
        # Wrapping in parentheses is essential when `keyword` contains " OR "
        # (from multi-tag selection) — without it, Google parses
        # "Steel OR RINL site:x.com" as "Steel OR (RINL site:x.com)", so
        # the site restriction only applies to the second half of the OR
        # expression and the newspaper filter silently stops working for
        # any keyword before the first "OR". Parenthesizing always,
        # even for a single-term keyword, is harmless and avoids this
        # class of bug entirely.
        query = f"({keyword}) site:{domain}" if domain else keyword
        locale = _LOCALE_BY_LANGUAGE.get(language, _LOCALE_BY_LANGUAGE["en"])

        url = (
            f"{RSS_BASE_URL}?q={quote_plus(query)}"
            f"&hl={locale['hl']}&gl={locale['gl']}&ceid={locale['ceid']}"
        )

        try:
            response = httpx.get(
                url,
                timeout=10,
                # httpx does NOT follow redirects by default (unlike the
                # `requests` library) — Google News RSS can respond with a
                # 302 (observed in practice, cause not fully confirmed;
                # possibly a regional/consent redirect), and without this,
                # that redirect was being treated as an outright failure
                # instead of being followed to the actual feed content.
                follow_redirects=True,
                headers={"User-Agent": "NewsPulse/1.0 (RINL internal tool)"},
            )
        except httpx.HTTPError as exc:
            raise NewsProviderError(f"Google News RSS request failed: {exc}") from exc

        if response.status_code != 200:
            raise NewsProviderError(f"Google News RSS returned HTTP {response.status_code}.")

        try:
            root = ElementTree.fromstring(response.content)
        except ElementTree.ParseError as exc:
            raise NewsProviderError(f"Could not parse Google News RSS feed: {exc}") from exc

        items = root.findall("./channel/item")[:max_results]
        articles = []
        for item in items:
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            description = _strip_html(item.findtext("description") or "")

            source_el = item.find("source")
            if source_el is not None and source_el.text:
                source_name = source_el.text.strip()
            elif " - " in title:
                # Fallback: Google's <title> is usually "Headline - Source".
                source_name = title.rsplit(" - ", 1)[-1].strip()
            else:
                source_name = "Google News"

            pub_date_raw = item.findtext("pubDate")
            published_at = None
            if pub_date_raw:
                try:
                    published_at = parsedate_to_datetime(pub_date_raw)
                except (TypeError, ValueError):
                    published_at = None

            articles.append(
                NormalizedArticle(
                    title=title,
                    source_name=source_name,
                    url=link,
                    description=description or None,
                    image_url=None,  # not available from this feed
                    published_at=published_at,
                    language=language,
                )
            )
        return articles
