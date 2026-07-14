"""Tests for app/api/routes/news.py."""


def test_search_requires_auth(client):
    response = client.get("/api/v1/news/search", params={"keyword": "steel"})
    assert response.status_code == 401


def test_newsdata_provider_never_sends_domain_param(monkeypatch):
    """
    Regression guard: NewsData.io's `domain` filter appears to only
    accept domains from their own internal registered-source list and
    returns a 422 for domains it doesn't recognize (observed with
    andhrajyothy.com in production, while other newspapers' domains
    worked) — so this provider must never send it. Newspaper filtering
    for NewsData.io relies entirely on the aggregator's own post-fetch
    verification instead (same approach already used for GNews).
    """
    import httpx

    from app.services.news.newsdata_provider import NewsDataProvider
    import app.core.config as config_mod

    monkeypatch.setattr(config_mod.settings, "NEWSDATA_API_KEY", "fake-key")
    captured_params = {}

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"status": "success", "results": []}

    def fake_get(url, params=None, **kwargs):
        captured_params.update(params or {})
        return FakeResponse()

    monkeypatch.setattr(httpx, "get", fake_get)
    NewsDataProvider().search(
        keyword="test", language="te", domain="andhrajyothy.com", max_results=10
    )

    assert "domain" not in captured_params


def test_newsdata_failure_with_newspaper_filter_falls_through_to_rss(
    client, register_user, monkeypatch
):
    """
    End-to-end reproduction of the real bug: a newspaper-filtered search
    where NewsData.io errors out (any reason) must still succeed via the
    RSS fallback, not surface as "no articles found" to the user.
    """
    import httpx

    import app.core.config as config_mod

    monkeypatch.setattr(config_mod.settings, "NEWSDATA_API_KEY", "fake-key")

    class NewsDataErrorResponse:
        status_code = 422

        def json(self):
            return {"status": "error", "message": "Invalid domain"}

    RSS_FEED = """<?xml version="1.0"?><rss><channel>
    <item><title>Andhra Jyothy story</title><link>https://news.google.com/rss/articles/a?oc=5</link>
    <pubDate>Fri, 04 Jul 2026 06:30:00 GMT</pubDate><description>d</description>
    <source url="https://andhrajyothy.com">Andhra Jyothy</source></item>
    </channel></rss>""".encode()

    class RSSResponse:
        status_code = 200
        content = RSS_FEED

    def fake_get(url, **kwargs):
        if "newsdata.io" in url:
            return NewsDataErrorResponse()
        return RSSResponse()

    monkeypatch.setattr(httpx, "get", fake_get)

    _, headers = register_user()
    response = client.get(
        "/api/v1/news/search",
        params={"keyword": "test", "language": "te", "newspaper": "andhra_jyothy"},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["provider_used"] == "google_rss"
    assert len(body["articles"]) == 1
    assert body["articles"][0]["source_name"] == "Andhra Jyothy"


def test_search_falls_back_to_rss_with_no_api_keys(client, register_user, mock_rss):
    _, headers = register_user()
    response = client.get(
        "/api/v1/news/search", params={"keyword": "steel", "language": "en"}, headers=headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["provider_used"] == "google_rss"
    assert len(body["articles"]) == 2


def test_rss_requests_follow_redirects(client, register_user, monkeypatch):
    """
    Regression guard: httpx (unlike the `requests` library) does NOT
    follow redirects by default. Google News RSS has been observed
    returning a 302, which — without follow_redirects=True — was
    treated as an outright provider failure instead of being followed
    to the real feed content, breaking search (most visibly for
    Telugu/Hindi, where RSS is the only provider active without paid
    API keys). If this assertion ever fails, that protection was
    accidentally removed.
    """
    import httpx

    from app.services.news.google_rss_provider import GoogleNewsRSSProvider

    captured_kwargs = {}

    class FakeResponse:
        status_code = 200
        content = b"<rss><channel></channel></rss>"

    def fake_get(url, **kwargs):
        captured_kwargs.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr(httpx, "get", fake_get)
    GoogleNewsRSSProvider().search(keyword="test", language="en", domain=None, max_results=10)

    assert captured_kwargs.get("follow_redirects") is True


def test_search_empty_result_shows_generic_notice_when_provider_worked_fine(client, register_user, monkeypatch):
    """A provider that ran successfully but genuinely found nothing (e.g.
    an empty RSS <channel>) should get the plain, friendly notice — not
    be reported as if something failed."""
    import httpx

    class EmptyFeedResponse:
        status_code = 200
        content = b'<?xml version="1.0"?><rss><channel></channel></rss>'

    monkeypatch.setattr(httpx, "get", lambda *a, **kw: EmptyFeedResponse())

    _, headers = register_user()
    response = client.get(
        "/api/v1/news/search",
        params={"keyword": "an extremely obscure query", "language": "en"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["notice"] == "No articles found. Try a different keyword, language, or date range."


def test_search_empty_result_surfaces_real_provider_failure_in_notice(client, register_user, monkeypatch):
    """When a provider actually fails (bad response, parse error, etc.),
    that reason should be visible in the notice rather than hidden behind
    a generic 'no results' message — this is what makes something like a
    silently rate-limited RSS feed diagnosable instead of looking like an
    ordinary empty search."""
    import httpx

    class BrokenResponse:
        status_code = 503

    monkeypatch.setattr(httpx, "get", lambda *a, **kw: BrokenResponse())

    _, headers = register_user()
    response = client.get(
        "/api/v1/news/search", params={"keyword": "steel", "language": "en"}, headers=headers
    )
    assert response.status_code == 200
    notice = response.json()["notice"]
    assert notice is not None
    assert "issue" in notice
    assert "google_rss" in notice


def test_search_records_history(client, register_user, mock_rss, db_session_factory):
    _, headers = register_user()
    client.get(
        "/api/v1/news/search",
        params={"keyword": "steel", "language": "en", "newspaper": "the_hindu", "edition": "Visakhapatnam"},
        headers=headers,
    )

    from app.models.search_history import SearchHistory

    db = db_session_factory()
    rows = db.query(SearchHistory).all()
    assert len(rows) == 1
    assert rows[0].keyword == "steel"
    assert rows[0].newspaper == "the_hindu"
    assert rows[0].edition == "Visakhapatnam"
    db.close()


def test_search_newspaper_language_mismatch_rejected(client, register_user):
    _, headers = register_user()
    response = client.get(
        "/api/v1/news/search",
        params={"keyword": "steel", "language": "hi", "newspaper": "the_hindu"},
        headers=headers,
    )
    assert response.status_code == 422


def test_search_edition_without_newspaper_is_now_allowed(client, register_user, mock_rss):
    _, headers = register_user()
    response = client.get(
        "/api/v1/news/search",
        params={"keyword": "steel", "edition": "Visakhapatnam"},
        headers=headers,
    )
    assert response.status_code == 200


def test_search_unrecognized_edition_without_newspaper_rejected(client, register_user):
    _, headers = register_user()
    response = client.get(
        "/api/v1/news/search",
        params={"keyword": "steel", "edition": "Not A Real Place"},
        headers=headers,
    )
    assert response.status_code == 422


def test_search_unknown_edition_for_newspaper_rejected(client, register_user):
    _, headers = register_user()
    response = client.get(
        "/api/v1/news/search",
        params={"keyword": "steel", "newspaper": "the_hindu", "edition": "Nonexistent City"},
        headers=headers,
    )
    assert response.status_code == 422


def test_search_custom_date_filter_requires_both_dates(client, register_user):
    _, headers = register_user()
    response = client.get(
        "/api/v1/news/search",
        params={"keyword": "steel", "date_filter": "custom"},
        headers=headers,
    )
    assert response.status_code == 422


def test_search_custom_date_range_rejects_to_before_from(client, register_user):
    _, headers = register_user()
    response = client.get(
        "/api/v1/news/search",
        params={
            "keyword": "steel",
            "date_filter": "custom",
            "date_from": "2026-07-05",
            "date_to": "2026-07-01",
        },
        headers=headers,
    )
    assert response.status_code == 422


def test_search_custom_date_range_accepts_valid_range(client, register_user, mock_rss):
    _, headers = register_user()
    response = client.get(
        "/api/v1/news/search",
        params={
            "keyword": "steel",
            "date_filter": "custom",
            "date_from": "2026-07-01",
            "date_to": "2026-07-10",
        },
        headers=headers,
    )
    assert response.status_code == 200


def test_newspapers_list_filters_by_language(client):
    response = client.get("/api/v1/news/newspapers", params={"language": "te"})
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 4
    assert all(n["language"] == "te" for n in body)


def test_tags_list_includes_predefined(client, register_user):
    _, headers = register_user()
    response = client.get("/api/v1/news/tags", headers=headers)
    assert response.status_code == 200
    predefined = [t for t in response.json() if not t["is_custom"]]
    assert len(predefined) == 23


def test_tags_are_language_specific(client, register_user):
    _, headers = register_user()

    english = client.get("/api/v1/news/tags", params={"language": "en"}, headers=headers).json()
    telugu = client.get("/api/v1/news/tags", params={"language": "te"}, headers=headers).json()
    hindi = client.get("/api/v1/news/tags", params={"language": "hi"}, headers=headers).json()

    english_predefined = {t["tag"] for t in english if not t["is_custom"]}
    telugu_predefined = {t["tag"] for t in telugu if not t["is_custom"]}
    hindi_predefined = {t["tag"] for t in hindi if not t["is_custom"]}

    assert "Steel" in english_predefined
    assert len(telugu_predefined) == 23
    assert len(hindi_predefined) == 23
    # Telugu and Hindi tag sets should actually differ from English (real
    # translations, not just the English list repeated under a different param).
    assert telugu_predefined != english_predefined
    assert hindi_predefined != english_predefined
    assert telugu_predefined != hindi_predefined


def test_custom_tags_visible_regardless_of_language(client, register_user):
    _, headers = register_user()
    client.post("/api/v1/news/tags", json={"tag": "My Custom Tag"}, headers=headers)

    for lang in ("en", "te", "hi"):
        tags = client.get("/api/v1/news/tags", params={"language": lang}, headers=headers).json()
        assert any(t["tag"] == "My Custom Tag" and t["is_custom"] for t in tags)


def test_newspapers_fetches_correctly_for_every_language(client):
    for lang, expected_count in [("en", 5), ("te", 4), ("hi", 3)]:
        response = client.get("/api/v1/news/newspapers", params={"language": lang})
        assert response.status_code == 200
        body = response.json()
        assert len(body) == expected_count, f"{lang} returned {len(body)} newspapers, expected {expected_count}"
        assert all(n["language"] == lang for n in body)


def test_languages_endpoint_returns_all_three(client):
    response = client.get("/api/v1/news/languages")
    assert response.status_code == 200
    codes = {lang["code"] for lang in response.json()}
    assert codes == {"en", "te", "hi"}


def test_newspapers_accepts_display_name_not_just_code(client):
    by_code = client.get("/api/v1/news/newspapers", params={"language": "te"}).json()
    by_name = client.get("/api/v1/news/newspapers", params={"language": "Telugu"}).json()
    by_name_lower = client.get("/api/v1/news/newspapers", params={"language": "telugu"}).json()

    assert {n["key"] for n in by_code} == {n["key"] for n in by_name} == {n["key"] for n in by_name_lower}


def test_newspapers_rejects_unknown_language(client):
    response = client.get("/api/v1/news/newspapers", params={"language": "klingon"})
    assert response.status_code == 422


def test_editions_returns_exact_required_lists(client):
    cases = {
        "the_hindu": {"Visakhapatnam", "Hyderabad", "Chennai", "Bengaluru", "Delhi"},
        "times_of_india": {"Hyderabad", "Mumbai", "Delhi", "Chennai", "Bengaluru", "Visakhapatnam"},
        "eenadu": {
            "Visakhapatnam", "Gajuwaka", "Ukkunagaram", "Anakapalle",
            "Vizianagaram", "Srikakulam", "Vijayawada", "Hyderabad",
        },
        "sakshi": {"Visakhapatnam", "Hyderabad", "Vijayawada", "Tirupati", "Kurnool"},
        "dainik_jagran": {"Delhi", "Lucknow", "Kanpur", "Patna", "Varanasi"},
    }
    for newspaper_key, expected_editions in cases.items():
        response = client.get("/api/v1/news/editions", params={"newspaper": newspaper_key})
        assert response.status_code == 200
        assert set(response.json()["editions"]) == expected_editions, newspaper_key


def test_editions_for_unknown_newspaper_is_404(client):
    response = client.get("/api/v1/news/editions", params={"newspaper": "not_a_real_newspaper"})
    assert response.status_code == 404


def test_editions_for_newspaper_with_none_returns_empty_list_not_error(client, db_session_factory):
    from app.models.newspaper import Newspaper

    db = db_session_factory()
    db.add(
        Newspaper(
            key="no_editions_paper",
            label="No Editions Paper",
            language="en",
            domain="example.com",
            edition_query_supported=False,
        )
    )
    db.commit()
    db.close()

    response = client.get("/api/v1/news/editions", params={"newspaper": "no_editions_paper"})
    assert response.status_code == 200
    assert response.json()["editions"] == []


def test_editions_without_newspaper_param_returns_union_across_all(client):
    response = client.get("/api/v1/news/editions")
    assert response.status_code == 200
    body = response.json()
    assert body["newspaper"] is None
    # "Visakhapatnam" appears in multiple newspapers' lists (The Hindu,
    # Times of India, Eenadu, Sakshi) but should be listed once.
    assert body["editions"].count("Visakhapatnam") == 1
    assert "Hyderabad" in body["editions"]


def test_search_with_newspaper_only_returns_matching_source_articles(client, register_user, monkeypatch):
    """
    The core "newspaper filter not working" bug: mixed-source results
    (e.g. from a provider that doesn't truly restrict by domain) must be
    filtered down to only the requested outlet before reaching the user.
    """
    import httpx

    MIXED_SOURCE_RSS = b"""<?xml version="1.0"?><rss><channel>
    <item><title>Steel story from The Hindu</title><link>https://news.google.com/rss/articles/a?oc=5</link>
    <pubDate>Fri, 04 Jul 2026 06:30:00 GMT</pubDate><description>d</description>
    <source url="https://thehindu.com">The Hindu</source></item>
    <item><title>Steel story from Times of India</title><link>https://news.google.com/rss/articles/b?oc=5</link>
    <pubDate>Fri, 04 Jul 2026 06:00:00 GMT</pubDate><description>d</description>
    <source url="https://timesofindia.com">Times of India</source></item>
    <item><title>Another Hindu story</title><link>https://news.google.com/rss/articles/c?oc=5</link>
    <pubDate>Fri, 04 Jul 2026 05:00:00 GMT</pubDate><description>d</description>
    <source url="https://thehindu.com">The Hindu</source></item>
    </channel></rss>"""

    class FakeResponse:
        status_code = 200
        content = MIXED_SOURCE_RSS

    monkeypatch.setattr(httpx, "get", lambda *a, **kw: FakeResponse())

    _, headers = register_user()
    response = client.get(
        "/api/v1/news/search",
        params={"keyword": "steel", "newspaper": "the_hindu"},
        headers=headers,
    )
    assert response.status_code == 200
    articles = response.json()["articles"]
    assert len(articles) == 2
    assert all(a["source_name"] == "The Hindu" for a in articles)


def test_multi_tag_or_query_still_respects_newspaper_filter(client, register_user, monkeypatch):
    """Regression test for the OR/site: precedence bug — a multi-tag (OR)
    search with a newspaper selected must not leak off-domain results."""
    import httpx

    MIXED_SOURCE_RSS = b"""<?xml version="1.0"?><rss><channel>
    <item><title>Steel story - The Hindu</title><link>https://news.google.com/rss/articles/a?oc=5</link>
    <pubDate>Fri, 04 Jul 2026 06:30:00 GMT</pubDate><description>d</description>
    <source url="https://thehindu.com">The Hindu</source></item>
    <item><title>RINL story - Sakshi</title><link>https://news.google.com/rss/articles/b?oc=5</link>
    <pubDate>Fri, 04 Jul 2026 06:00:00 GMT</pubDate><description>d</description>
    <source url="https://sakshi.com">Sakshi</source></item>
    </channel></rss>"""

    class FakeResponse:
        status_code = 200
        content = MIXED_SOURCE_RSS

    monkeypatch.setattr(httpx, "get", lambda *a, **kw: FakeResponse())

    _, headers = register_user()
    response = client.get(
        "/api/v1/news/search",
        params={"keyword": "Steel OR RINL", "newspaper": "the_hindu"},
        headers=headers,
    )
    assert response.status_code == 200
    articles = response.json()["articles"]
    assert len(articles) == 1
    assert articles[0]["source_name"] == "The Hindu"


def test_search_rejects_edition_not_belonging_to_newspaper(client, register_user):
    _, headers = register_user()
    response = client.get(
        "/api/v1/news/search",
        params={"keyword": "steel", "newspaper": "the_hindu", "edition": "Mumbai"},  # Mumbai isn't a Hindu edition
        headers=headers,
    )
    assert response.status_code == 422


def test_add_and_delete_custom_tag(client, register_user):
    _, headers = register_user()

    created = client.post("/api/v1/news/tags", json={"tag": "Slag Utilization"}, headers=headers)
    assert created.status_code == 201
    tag_id = created.json()["id"]

    listing = client.get("/api/v1/news/tags", headers=headers)
    assert any(t["id"] == tag_id for t in listing.json())

    deleted = client.delete(f"/api/v1/news/tags/{tag_id}", headers=headers)
    assert deleted.status_code == 200

    listing_after = client.get("/api/v1/news/tags", headers=headers)
    assert not any(t.get("id") == tag_id for t in listing_after.json())


def test_cannot_add_predefined_tag_as_custom(client, register_user):
    _, headers = register_user()
    response = client.post("/api/v1/news/tags", json={"tag": "Steel"}, headers=headers)
    assert response.status_code == 409


def test_cannot_add_duplicate_custom_tag(client, register_user):
    _, headers = register_user()
    client.post("/api/v1/news/tags", json={"tag": "My Tag"}, headers=headers)
    response = client.post("/api/v1/news/tags", json={"tag": "my tag"}, headers=headers)
    assert response.status_code == 409


def test_custom_tags_are_per_user(client, register_user):
    _, headers_a = register_user(email="a@vizagsteel.com")
    _, headers_b = register_user(email="b@vizagsteel.com")

    client.post("/api/v1/news/tags", json={"tag": "Only A's Tag"}, headers=headers_a)

    tags_b = client.get("/api/v1/news/tags", headers=headers_b).json()
    assert not any(t["tag"] == "Only A's Tag" for t in tags_b)
