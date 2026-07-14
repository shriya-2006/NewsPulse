"""Tests for app/services/search_cache_service.py and the cleanup job."""

from datetime import datetime, timedelta, timezone


def test_second_identical_search_does_not_call_provider_again(client, register_user, monkeypatch):
    """The core caching behavior: the exact same search run twice should
    only hit the live provider once."""
    import httpx

    call_count = {"n": 0}

    RSS_FEED = """<?xml version="1.0"?><rss><channel>
    <item><title>Steel story - The Hindu</title><link>https://x/1</link>
    <pubDate>Fri, 04 Jul 2026 06:30:00 GMT</pubDate><description>d</description>
    <source url="https://thehindu.com">The Hindu</source></item>
    </channel></rss>""".encode()

    class FakeResponse:
        status_code = 200
        content = RSS_FEED

    def fake_get(*a, **kw):
        call_count["n"] += 1
        return FakeResponse()

    monkeypatch.setattr(httpx, "get", fake_get)

    _, headers = register_user()

    first = client.get("/api/v1/news/search", params={"keyword": "steel", "language": "en"}, headers=headers)
    second = client.get("/api/v1/news/search", params={"keyword": "steel", "language": "en"}, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["from_cache"] is False
    assert second.json()["from_cache"] is True
    assert first.json()["articles"] == second.json()["articles"]
    assert call_count["n"] == 1  # only the FIRST search actually hit the network


def test_different_search_params_do_not_share_a_cache_entry(client, register_user, mock_rss):
    """Different keyword/newspaper/etc. must never accidentally serve
    each other's cached results."""
    _, headers = register_user()

    r1 = client.get("/api/v1/news/search", params={"keyword": "steel", "language": "en"}, headers=headers)
    r2 = client.get("/api/v1/news/search", params={"keyword": "coal", "language": "en"}, headers=headers)

    assert r1.json()["from_cache"] is False
    assert r2.json()["from_cache"] is False  # different keyword -> genuinely different cache key


def test_stale_cache_entry_triggers_a_fresh_fetch(client, register_user, monkeypatch, db_session_factory):
    """A cache entry older than SEARCH_CACHE_FRESHNESS_HOURS must not be
    served — the search should hit the provider again."""
    import httpx

    import app.core.config as config_mod

    monkeypatch.setattr(config_mod.settings, "SEARCH_CACHE_FRESHNESS_HOURS", 3)

    call_count = {"n": 0}
    RSS_FEED = """<?xml version="1.0"?><rss><channel>
    <item><title>Steel story - The Hindu</title><link>https://x/1</link>
    <pubDate>Fri, 04 Jul 2026 06:30:00 GMT</pubDate><description>d</description>
    <source url="https://thehindu.com">The Hindu</source></item>
    </channel></rss>""".encode()

    class FakeResponse:
        status_code = 200
        content = RSS_FEED

    def fake_get(*a, **kw):
        call_count["n"] += 1
        return FakeResponse()

    monkeypatch.setattr(httpx, "get", fake_get)

    _, headers = register_user()
    client.get("/api/v1/news/search", params={"keyword": "steel", "language": "en"}, headers=headers)
    assert call_count["n"] == 1

    # Manually age the cache entry past the freshness window.
    from app.models.cached_search import CachedSearch

    db = db_session_factory()
    entry = db.query(CachedSearch).first()
    entry.fetched_at = datetime.now(timezone.utc) - timedelta(hours=4)
    db.commit()
    db.close()

    second = client.get("/api/v1/news/search", params={"keyword": "steel", "language": "en"}, headers=headers)
    assert second.json()["from_cache"] is False
    assert call_count["n"] == 2  # stale cache -> refetched


def test_cache_key_is_stable_across_different_query_param_object_identity(client, register_user, mock_rss):
    """Sanity check that the same logical query always produces a cache
    hit, not just an accidental one-off — run it three times."""
    _, headers = register_user()
    results = [
        client.get(
            "/api/v1/news/search",
            params={"keyword": "steel", "language": "en", "date_filter": "any"},
            headers=headers,
        )
        for _ in range(3)
    ]
    from_cache_flags = [r.json()["from_cache"] for r in results]
    assert from_cache_flags == [False, True, True]


def test_pagination_works_over_a_cached_result_set(client, register_user, monkeypatch):
    """Page 2 of a cached search must come from the cache too, not
    trigger a second live fetch."""
    import httpx

    call_count = {"n": 0}
    items = "".join(
        f"""<item><title>Story {i} - The Hindu</title><link>https://x/{i}</link>
        <pubDate>Fri, 04 Jul 2026 06:30:00 GMT</pubDate><description>d</description>
        <source url="https://thehindu.com">The Hindu</source></item>"""
        for i in range(15)
    )
    RSS_FEED = f'<?xml version="1.0"?><rss><channel>{items}</channel></rss>'.encode()

    class FakeResponse:
        status_code = 200
        content = RSS_FEED

    def fake_get(*a, **kw):
        call_count["n"] += 1
        return FakeResponse()

    monkeypatch.setattr(httpx, "get", fake_get)

    _, headers = register_user()
    page1 = client.get(
        "/api/v1/news/search",
        params={"keyword": "steel", "language": "en", "page": 1, "page_size": 10},
        headers=headers,
    )
    page2 = client.get(
        "/api/v1/news/search",
        params={"keyword": "steel", "language": "en", "page": 2, "page_size": 10},
        headers=headers,
    )

    assert len(page1.json()["articles"]) == 10
    assert len(page2.json()["articles"]) == 5
    assert page2.json()["from_cache"] is True
    assert call_count["n"] == 1  # page 2 came from the same cached fetch as page 1


def test_empty_results_are_not_cached(client, register_user, monkeypatch):
    """An empty result shouldn't be remembered — the next attempt should
    try again rather than being stuck seeing 'no results' from a stale
    empty cache entry."""
    import httpx

    call_count = {"n": 0}

    class EmptyResponse:
        status_code = 200
        content = b'<?xml version="1.0"?><rss><channel></channel></rss>'

    def fake_get(*a, **kw):
        call_count["n"] += 1
        return EmptyResponse()

    monkeypatch.setattr(httpx, "get", fake_get)

    _, headers = register_user()
    client.get("/api/v1/news/search", params={"keyword": "nonexistent", "language": "en"}, headers=headers)
    client.get("/api/v1/news/search", params={"keyword": "nonexistent", "language": "en"}, headers=headers)

    assert call_count["n"] == 2  # neither call was served from cache


def test_admin_cleanup_endpoint_requires_admin(client, register_user):
    _, headers = register_user()
    response = client.post("/api/v1/admin/cleanup-old-articles", headers=headers)
    assert response.status_code == 403


def test_admin_cleanup_endpoint_runs_successfully(client, admin_headers):
    response = client.post("/api/v1/admin/cleanup-old-articles", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert "deleted_cached_searches" in body
    assert "deleted_articles" in body


def test_cleanup_deletes_old_orphaned_articles_but_preserves_report_articles(
    client, register_user, db_session_factory, monkeypatch
):
    """The actual cleanup logic, exercised directly: an old article that
    was never used in a report gets deleted; an old article that WAS
    used in a report is preserved regardless of age."""
    from app.models.report import Article
    from app.scripts.cleanup_old_articles import run_cleanup

    _, headers = register_user()

    # Generate a real report so one article becomes "protected".
    report_payload = {
        "keyword": "steel",
        "language": "en",
        "articles": [
            {
                "title": "Protected article",
                "source_name": "The Hindu",
                "url": "https://example.com/protected",
                "description": "desc",
                "image_url": None,
                "published_at": "2026-01-01T00:00:00",
                "content": None,
            }
        ],
    }
    client.post("/api/v1/reports/generate", json=report_payload, headers=headers)

    db = db_session_factory()
    # Add a second, unprotected old article directly.
    orphan = Article(
        source_name="Sakshi",
        title="Orphaned old article",
        url="https://example.com/orphan",
        description="old",
        language="en",
        fetched_at=datetime.now(timezone.utc) - timedelta(days=200),
    )
    db.add(orphan)
    db.commit()

    # Age BOTH articles past the retention window.
    old_cutoff = datetime.now(timezone.utc) - timedelta(days=200)
    db.query(Article).update({Article.fetched_at: old_cutoff})
    db.commit()

    result = run_cleanup(retention_days=90, db=db)
    assert result["deleted_articles"] == 1  # only the orphan

    remaining_urls = {a.url for a in db.query(Article).all()}
    assert "https://example.com/protected" in remaining_urls
    assert "https://example.com/orphan" not in remaining_urls
    db.close()
