"""
Request/response schemas for the News Search and Tags endpoints.
"""

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class Language(str, Enum):
    en = "en"
    te = "te"
    hi = "hi"


class DateFilter(str, Enum):
    any = "any"
    today = "today"
    yesterday = "yesterday"
    custom = "custom"


# ---------------------------------------------------------------------------
# Articles
# ---------------------------------------------------------------------------
class ArticleOut(BaseModel):
    title: str
    source_name: str
    url: str
    description: str | None = None
    image_url: str | None = None
    published_at: datetime | None = None
    language: str
    content: str | None = None


class LanguageOut(BaseModel):
    code: str
    label: str


class NewspaperOut(BaseModel):
    key: str
    label: str
    language: str
    edition_filter_supported: bool


class EditionsResponse(BaseModel):
    newspaper: str | None  # the newspaper key that was queried, or None for "all editions"
    editions: list[str]


class SearchResponse(BaseModel):
    articles: list[ArticleOut]
    page: int
    page_size: int
    total_results: int  # count returned by the winning provider before pagination
    has_more: bool
    provider_used: str | None
    keyword: str
    language: str
    newspaper: str | None
    edition: str | None
    date_filter: str
    # Set only when every provider failed/returned nothing, to help
    # surface *why* (e.g. "no API keys configured and RSS had no results")
    # without treating it as an HTTP error.
    notice: str | None = None
    # True when this response was served from the database cache
    # instead of calling a live provider (see search_cache_service.py) —
    # purely informational, doesn't change how the frontend should treat
    # the results otherwise.
    from_cache: bool = False


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------
class TagOut(BaseModel):
    id: int | None = None  # None for predefined tags (they aren't DB rows)
    tag: str
    is_custom: bool


class CreateTagRequest(BaseModel):
    tag: str = Field(..., min_length=1, max_length=100)

    @field_validator("tag")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Tag cannot be blank.")
        return value.strip()


class MessageResponse(BaseModel):
    message: str
