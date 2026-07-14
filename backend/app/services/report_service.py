"""
Report generation business logic: takes the selected articles + search
context, caches the articles in the DB (deduped by URL), writes the
Report row, renders the PDF, and stores it on disk.
"""

import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.report import Article, Report
from app.models.user import User
from app.schemas.report import GenerateReportRequest
from app.services.pdf_service import render_report_pdf
from app.services import newspaper_service

LANGUAGE_LABELS = {"en": "English", "te": "Telugu", "hi": "Hindi"}


def _reports_root() -> Path:
    path = Path(settings.REPORTS_DIR)
    if not path.is_absolute():
        # Relative to backend/ (three levels up from this file: services -> app -> backend).
        path = Path(__file__).resolve().parent.parent.parent / path
    return path


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return slug or "report"


# GNews (and some other providers) truncate `content` on free/lower
# tiers with a trailing marker like "... [+1348 chars]" — stripped so it
# never shows up as literal noise in a report.
_TRUNCATION_SUFFIX = re.compile(r"\s*\[\+\d+\s*chars?\]\s*$", re.IGNORECASE)


def _resolve_content(article_in) -> str | None:
    """
    Returns the fullest text available for one article, without
    scraping the original page — just making better use of what the
    news provider already gave us:

    - `content` (GNews/NewsData.io, mainly a paid-plan field) is often
      truncated; its truncation marker is stripped first.
    - `description` is sometimes a fuller standalone summary than what's
      left of a truncated `content`.
    - When both are present and say something different, both are kept
      (content, then description) rather than picking only one — this
      is what actually maximizes the text in the report. When one is a
      near-duplicate of the other (e.g. content is just description
      with a few more words), only the longer one is kept, so the PDF
      doesn't visibly repeat the same sentence twice.
    """
    content = article_in.content
    if content:
        content = _TRUNCATION_SUFFIX.sub("", content).strip() or None

    description = (article_in.description or "").strip() or None

    if content and description:
        if description.lower() in content.lower():
            return content
        if content.lower() in description.lower():
            return description
        return f"{content}\n\n{description}"

    return content or description


def _get_or_create_article(db: Session, article_in, effective_content: str | None) -> Article:
    """Reuses an existing cached Article row by URL, or creates one."""
    existing = db.query(Article).filter(Article.url == article_in.url).first()
    if existing:
        # Refresh with the latest data in case content/description improved
        # since it was first cached (e.g. a paid content field arrived later).
        existing.title = article_in.title
        existing.source_name = article_in.source_name
        existing.description = article_in.description
        existing.image_url = article_in.image_url
        existing.content = effective_content or existing.content
        return existing

    row = Article(
        source_name=article_in.source_name,
        title=article_in.title,
        url=article_in.url,
        description=article_in.description,
        image_url=article_in.image_url,
        content=effective_content,
        published_at=article_in.published_at,
    )
    db.add(row)
    return row


def generate_report(db: Session, user: User, request: GenerateReportRequest) -> Report:
    newspaper_label = "All newspapers"
    if request.newspaper:
        meta = newspaper_service.get_newspaper_by_key(db, request.newspaper)
        if not meta:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown newspaper."
            )
        newspaper_label = meta.label

    # --- Resolve full text once per article, reused for both the cached
    # DB row and the PDF context. ---
    resolved_contents = [_resolve_content(a) for a in request.articles]

    # --- Cache/dedupe articles, build the Report row ---
    article_rows = [
        _get_or_create_article(db, a, content)
        for a, content in zip(request.articles, resolved_contents)
    ]

    now = datetime.now(timezone.utc)
    title = f"{request.keyword.title()} — News Report ({now.strftime('%d %b %Y')})"

    report = Report(
        user_id=user.id,
        title=title,
        keyword=request.keyword,
        language=request.language.value,
        newspaper=request.newspaper,
        edition=request.edition,
        file_path="",  # filled in after the PDF is written
        article_count=len(article_rows),
    )
    report.articles = article_rows
    db.add(report)
    db.flush()  # assigns report.id without committing yet

    # --- Render the PDF ---
    pdf_context = {
        "report_title": title,
        "generated_at": now.strftime("%d %B %Y, %I:%M %p UTC"),
        "keyword": request.keyword,
        "language": request.language.value,
        "language_label": LANGUAGE_LABELS.get(request.language.value, request.language.value),
        "newspaper_label": newspaper_label,
        "edition_label": request.edition or "All editions",
        "articles": [
            {
                "title": a.title,
                "source_name": a.source_name,
                "url": a.url,
                "description": a.description,
                "content": content,
                "published_at_label": (
                    a.published_at.strftime("%d %b %Y, %I:%M %p") if a.published_at else None
                ),
            }
            for a, content in zip(request.articles, resolved_contents)
        ],
    }

    filename = f"{report.id}-{slugify(request.keyword)}.pdf"
    output_path = _reports_root() / str(user.id) / filename
    render_report_pdf(context=pdf_context, output_path=output_path)

    report.file_path = str(output_path)
    db.commit()
    db.refresh(report)
    return report


def get_owned_report(db: Session, user_id: int, report_id: int) -> Report:
    report = db.query(Report).filter(Report.id == report_id, Report.user_id == user_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")
    return report


def list_reports(db: Session, user_id: int) -> list[Report]:
    return (
        db.query(Report)
        .filter(Report.user_id == user_id)
        .order_by(Report.generated_at.desc())
        .all()
    )
