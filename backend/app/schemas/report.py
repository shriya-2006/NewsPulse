"""
Request/response schemas for report generation.

`ReportArticleIn` intentionally mirrors `ArticleOut` from schemas/news.py —
the frontend already has the full article data from the search results
it's showing the user, so it sends that straight back rather than
requiring the backend to re-fetch from the news provider (which might
return different results by the time the report is generated, or fail).
"""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.news import Language


class ReportArticleIn(BaseModel):
    title: str
    source_name: str
    url: str
    description: str | None = None
    image_url: str | None = None
    published_at: datetime | None = None
    content: str | None = None


class GenerateReportRequest(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=255)
    language: Language
    newspaper: str | None = None  # key from /news/newspapers, for the cover page only
    edition: str | None = None
    articles: list[ReportArticleIn] = Field(..., min_length=1, max_length=100)


class ReportOut(BaseModel):
    id: int
    title: str
    keyword: str
    language: str
    newspaper: str | None
    edition: str | None
    article_count: int
    generated_at: datetime
    download_url: str
