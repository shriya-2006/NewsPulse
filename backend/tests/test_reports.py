"""Tests for app/api/routes/reports.py."""

from pathlib import Path

SAMPLE_ARTICLES = [
    {
        "title": "Steel output rises",
        "source_name": "The Hindu",
        "url": "https://example.com/article-1",
        "description": "Production increased this quarter.",
        "image_url": None,
        "published_at": "2026-07-04T06:30:00",
        "content": "Full article text about rising steel output at the plant this quarter.",
    },
    {
        "title": "Workers welcome expansion",
        "source_name": "The Hindu",
        "url": "https://example.com/article-2",
        "description": "Unions welcomed the announcement.",
        "image_url": None,
        "published_at": "2026-07-04T07:00:00",
        "content": None,
    },
]


def _generate(client, headers, articles=None):
    payload = {
        "keyword": "steel",
        "language": "en",
        "newspaper": "the_hindu",
        "edition": "Visakhapatnam",
        "articles": articles if articles is not None else SAMPLE_ARTICLES,
    }
    return client.post("/api/v1/reports/generate", json=payload, headers=headers)


def test_generate_report_requires_auth(client):
    response = client.post(
        "/api/v1/reports/generate",
        json={"keyword": "steel", "language": "en", "articles": SAMPLE_ARTICLES},
    )
    assert response.status_code == 401


def test_generate_report_returns_download_url(client, register_user):
    _, headers = register_user()
    response = _generate(client, headers)
    assert response.status_code == 200
    body = response.json()
    assert body["article_count"] == 2
    assert body["download_url"].endswith("/download")


def test_generate_report_rejects_empty_article_list(client, register_user):
    _, headers = register_user()
    response = _generate(client, headers, articles=[])
    assert response.status_code == 422


def test_download_report_returns_real_pdf(client, register_user):
    _, headers = register_user()
    report = _generate(client, headers).json()

    response = client.get(report["download_url"], headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content[:4] == b"%PDF"
    assert len(response.content) > 1000


def test_downloaded_pdf_contains_article_content(client, register_user, tmp_path):
    _, headers = register_user()
    report = _generate(client, headers).json()
    response = client.get(report["download_url"], headers=headers)

    pdf_path = tmp_path / "report.pdf"
    pdf_path.write_bytes(response.content)

    import subprocess

    text = subprocess.run(
        ["pdftotext", str(pdf_path), "-"], capture_output=True, text=True
    ).stdout
    assert "Steel output rises" in text
    assert "rising steel output" in text  # from the full content field
    assert "Workers welcome expansion" in text
    assert "Unions welcomed the announcement" in text  # fallback to description


def test_cannot_download_another_users_report(client, register_user):
    _, headers_a = register_user(email="a@vizagsteel.com")
    _, headers_b = register_user(email="b@vizagsteel.com")

    report = _generate(client, headers_a).json()
    response = client.get(report["download_url"], headers=headers_b)
    assert response.status_code == 404


def test_pdf_combines_truncated_content_and_distinct_description(client, register_user, tmp_path):
    """Maximizing available text: a GNews-style truncated `content` and a
    genuinely different `description` should both appear in the PDF,
    with the truncation marker stripped — rather than only ever showing
    whichever field the code happened to prefer."""
    _, headers = register_user()
    articles = [
        {
            "title": "RINL commissions new unit",
            "source_name": "The Hindu",
            "url": "https://example.com/truncated-article",
            "description": "Trade unions welcomed the capacity expansion as a boost for job security.",
            "image_url": None,
            "published_at": "2026-07-04T06:30:00",
            "content": "RINL commissioned a new unit today, marking a milestone [+1348 chars]",
        }
    ]
    report = _generate(client, headers, articles=articles).json()
    response = client.get(report["download_url"], headers=headers)

    pdf_path = tmp_path / "combined.pdf"
    pdf_path.write_bytes(response.content)
    import subprocess

    text = subprocess.run(["pdftotext", str(pdf_path), "-"], capture_output=True, text=True).stdout
    normalized = " ".join(text.split())  # collapse PDF line-wrapping before substring checks
    assert "RINL commissioned a new unit today, marking a milestone" in normalized
    assert "[+1348" not in normalized  # truncation marker stripped
    assert "Trade unions welcomed the capacity expansion" in normalized  # distinct description also kept


def test_list_reports_only_shows_own_reports(client, register_user):
    _, headers_a = register_user(email="a@vizagsteel.com")
    _, headers_b = register_user(email="b@vizagsteel.com")

    _generate(client, headers_a)

    assert len(client.get("/api/v1/reports", headers=headers_a).json()) == 1
    assert len(client.get("/api/v1/reports", headers=headers_b).json()) == 0


def test_same_article_reused_across_reports_not_duplicated(client, register_user, db_session_factory):
    _, headers = register_user()
    _generate(client, headers)
    _generate(client, headers)  # same articles, same URLs

    from app.models.report import Article

    db = db_session_factory()
    articles = db.query(Article).all()
    assert len(articles) == 2  # not 4 — deduped by URL
    db.close()


def test_html_special_characters_in_article_are_escaped_not_broken(client, register_user, tmp_path):
    _, headers = register_user()
    malicious_articles = [
        {
            "title": "Steel prices rise 5% <script>alert(1)</script> & shift",
            "source_name": "Test & Co",
            "url": "https://example.com/escape-test",
            "description": 'Contains <b>bold</b> & "quotes" that must be escaped',
            "image_url": None,
            "published_at": None,
            "content": None,
        }
    ]
    report = _generate(client, headers, articles=malicious_articles).json()
    response = client.get(report["download_url"], headers=headers)
    assert response.status_code == 200
    # The raw HTML must never appear as active markup in the source PDF
    # object stream — weasyprint escapes it into literal text.
    assert b"<script>" not in response.content


def test_pdf_template_declares_indic_script_fonts():
    """
    Regression guard: DejaVu Sans alone has no Devanagari/Telugu glyphs,
    and even a substitute font needs proper OpenType shaping rules for
    those scripts (plain glyph coverage isn't enough — conjuncts and
    vowel-sign reordering need real shaping support). If this ever
    reverts to a bare 'DejaVu Sans, sans-serif' stack, Hindi/Telugu
    report text can render with misplaced vowel signs, which a native
    reader would immediately notice as wrong. See backend/README.md's
    "Hindi/Telugu text in report PDFs" section.
    """
    template_path = Path(__file__).resolve().parent.parent / "app" / "templates" / "report_template.html"
    css = template_path.read_text(encoding="utf-8")
    assert "Noto Sans Devanagari" in css
    assert "Noto Sans Telugu" in css


def test_generate_hindi_report_produces_real_pdf(client, register_user, tmp_path):
    """End-to-end: a Hindi-language report with Devanagari article text
    actually produces a valid, non-trivial PDF — doesn't verify glyph
    shaping (pytest can't do visual inspection), but does catch total
    failures like template/encoding errors that only show up with
    non-Latin text."""
    _, headers = register_user()
    payload = {
        "keyword": "इस्पात",
        "language": "hi",
        "newspaper": "dainik_jagran",
        "edition": "Delhi",
        "articles": [
            {
                "title": "इस्पात उत्पादन में वृद्धि",
                "source_name": "Dainik Jagran",
                "url": "https://example.com/hindi-article",
                "description": "विशाखापत्तनम इस्पात संयंत्र में उत्पादन क्षमता में उल्लेखनीय वृद्धि हुई है।",
                "image_url": None,
                "published_at": "2026-07-04T06:30:00",
                "content": None,
            }
        ],
    }
    response = client.post("/api/v1/reports/generate", json=payload, headers=headers)
    assert response.status_code == 200
    report = response.json()

    download = client.get(report["download_url"], headers=headers)
    assert download.status_code == 200
    assert download.content[:4] == b"%PDF"
    assert len(download.content) > 1000
