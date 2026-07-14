"""
News search + tags + newspaper/edition hierarchy routes — all protected
except the pure reference-data ones (/languages, /newspapers, /editions),
which don't touch anything user-specific and are safe to call before
a search is even attempted.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.database import get_db
from app.models.search_history import SearchHistory
from app.models.user import User
from app.schemas.news import (
    ArticleOut,
    CreateTagRequest,
    DateFilter,
    EditionsResponse,
    Language,
    LanguageOut,
    MessageResponse,
    NewspaperOut,
    SearchResponse,
    TagOut,
)
from app.services import newspaper_service, search_cache_service, tag_service
from app.services.news.aggregator import search_news
from app.utils.newspaper_sources import get_predefined_tags

router = APIRouter(prefix="/news", tags=["News"])

# When populating a fresh cache entry, always fetch at least this many
# results — a cache entry is meant to serve several future page
# requests for the same query, not just the one page that happened to
# trigger the fetch. See the /search route for how this combines with
# the specific page actually requested.
SEARCH_CACHE_MIN_FETCH_SIZE = 40


# ---------------------------------------------------------------------------
# Cascading language -> newspaper -> edition hierarchy.
# Each level is its own endpoint, matching the required selection flow:
#   GET /languages  ->  GET /newspapers?language=X  ->  GET /editions?newspaper=Y
# Every response is read straight from the database (see
# app/services/newspaper_service.py) — nothing here is hardcoded, so a
# newly-inserted newspaper or edition shows up automatically with no
# frontend or backend code changes.
# ---------------------------------------------------------------------------
@router.get("/languages", response_model=list[LanguageOut])
def list_languages():
    return [LanguageOut(**lang) for lang in newspaper_service.list_languages()]


@router.get("/newspapers", response_model=list[NewspaperOut])
def list_newspapers(
    language: str | None = Query(
        default=None, description="Language code ('te') or name ('Telugu'), case-insensitive."
    ),
    db: Session = Depends(get_db),
):
    language_code = None
    if language:
        language_code = newspaper_service.normalize_language(language)
        if not language_code:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unknown language '{language}'.",
            )

    newspapers = newspaper_service.list_newspapers(db, language_code)
    return [
        NewspaperOut(
            key=n.key,
            label=n.label,
            language=n.language,
            edition_filter_supported=n.edition_query_supported,
        )
        for n in newspapers
    ]


@router.get("/editions", response_model=EditionsResponse)
def list_editions(
    newspaper: str | None = Query(
        default=None,
        description="Newspaper key from GET /news/newspapers. Omit to get every edition across all newspapers (for filtering by edition without picking a specific newspaper).",
    ),
    db: Session = Depends(get_db),
):
    if newspaper is None:
        return EditionsResponse(newspaper=None, editions=newspaper_service.list_all_editions(db))

    editions = newspaper_service.list_editions(db, newspaper)
    if editions is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown newspaper.")
    # An empty list is a valid, successful response — the frontend shows
    # "No editions available." rather than treating it as an error.
    return EditionsResponse(newspaper=newspaper, editions=editions)


@router.get("/search", response_model=SearchResponse)
def search(
    keyword: str = Query(..., min_length=2, max_length=255),
    language: Language = Query(default=Language.en),
    newspaper: str | None = Query(default=None, description="Key from GET /news/newspapers"),
    edition: str | None = Query(default=None, description="Must be one of GET /news/editions?newspaper=... for this newspaper"),
    date_filter: DateFilter = Query(default=DateFilter.any),
    date_from: date | None = Query(default=None, description="Required when date_filter='custom'"),
    date_to: date | None = Query(default=None, description="Required when date_filter='custom'; must be >= date_from"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=30),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    domain = None
    newspaper_label = None
    if newspaper:
        meta = newspaper_service.get_newspaper_by_key(db, newspaper)
        if not meta:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown newspaper.")
        if meta.language != language.value:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{meta.label} is a {meta.language} newspaper, not {language.value}.",
            )
        if edition:
            known_editions = {e.name for e in meta.editions}
            if edition not in known_editions:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"'{edition}' is not a known edition of {meta.label}.",
                )
        domain = meta.domain
        newspaper_label = meta.label
    elif edition:
        # Edition without a newspaper is allowed — it's validated against
        # every known edition across all newspapers instead of one
        # specific newspaper's list.
        if edition not in set(newspaper_service.list_all_editions(db)):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"'{edition}' is not a recognized edition.",
            )

    if date_filter == DateFilter.custom:
        if not date_from or not date_to:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="date_from and date_to are both required when date_filter is 'custom'.",
            )
        if date_to < date_from:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="date_to must be on or after date_from.",
            )

    # None of the three integrated providers support real per-edition
    # filtering (see edition_query_supported on the Newspaper model), so
    # an edition — with or without a specific newspaper — is folded into
    # the query text itself as a location hint instead. The keyword is
    # parenthesized first so this stays correct when it's an OR
    # expression from multi-tag selection (e.g. "(Steel OR RINL) Hyderabad"
    # means "(Steel OR RINL) AND Hyderabad", not "Steel OR (RINL Hyderabad)").
    effective_keyword = f"({keyword}) {edition}" if edition else keyword

    # --- Cache-aside: serve from the DB if a fresh-enough cached result
    # for this exact query already exists, instead of always hitting a
    # live provider. See app/services/search_cache_service.py for why —
    # short version: free-tier API quotas are small, and this also
    # reduces how often the (rate-limit-prone) RSS fallback gets hit.
    cache_key = search_cache_service.build_cache_key(
        keyword=effective_keyword,
        language=language.value,
        newspaper=newspaper,
        edition=edition,
        date_filter=date_filter.value,
        date_from=date_from,
        date_to=date_to,
    )
    cached_entry = search_cache_service.get_fresh_cached_search(db, cache_key)

    from_cache = False
    real_failures: set[str] = set()
    provider_errors: dict[str, str] = {}

    if cached_entry is not None:
        from_cache = True
        provider_used = cached_entry.provider_used
        all_articles = search_cache_service.cached_articles_as_normalized(cached_entry)
    else:
        # A fresh cache entry is meant to serve MULTIPLE future page
        # requests for this same query, not just whichever page happened
        # to trigger the fetch — so this always requests at least
        # SEARCH_CACHE_MIN_FETCH_SIZE results, on top of (not instead of)
        # whatever the specific requested page actually needs (relevant
        # for someone jumping straight to a deep page with a large
        # page_size). In-practice provider caps (e.g. GNews's free-tier
        # 10-per-request limit) still apply on top of this — this is a
        # ceiling we ask for, not a guarantee of how many come back.
        outcome = search_news(
            keyword=effective_keyword,
            language=language.value,
            domain=domain,
            newspaper_label=newspaper_label,
            date_filter=date_filter.value,
            date_from=date_from,
            date_to=date_to,
            max_results=max(page * page_size + 1, SEARCH_CACHE_MIN_FETCH_SIZE),
        )
        provider_used = outcome.provider_used
        all_articles = outcome.articles
        real_failures = outcome.real_failures
        provider_errors = outcome.provider_errors

        if all_articles:
            # Only cache genuine hits — an empty result isn't worth
            # remembering for SEARCH_CACHE_FRESHNESS_HOURS, since the
            # next attempt should just try again rather than being
            # stuck seeing "no results" from a stale empty cache entry.
            search_cache_service.store_search_result(
                db,
                cache_key=cache_key,
                keyword=effective_keyword,
                language=language.value,
                newspaper=newspaper,
                edition=edition,
                date_filter=date_filter.value,
                provider_used=provider_used,
                articles=all_articles,
            )

    start = (page - 1) * page_size
    page_articles = all_articles[start : start + page_size]
    has_more = len(all_articles) > start + page_size

    # Record this search regardless of whether it returned anything, and
    # regardless of whether it was served from cache — a zero-result
    # search is still meaningful for the admin dashboard's "most
    # searched keywords" metric later.
    db.add(
        SearchHistory(
            user_id=current_user.id,
            keyword=keyword,
            language=language.value,
            newspaper=newspaper,
            edition=edition,
            result_count=len(all_articles),
        )
    )
    db.commit()

    notice = None
    if not all_articles:
        # Distinguish "providers ran fine but genuinely found nothing" from
        # "a provider actually failed" (rate limiting, network error,
        # malformed response, etc.) using the aggregator's structural
        # real_failures set — not by guessing from error message text.
        # This is what makes something like a silently rate-limited RSS
        # feed diagnosable instead of looking identical to an honest
        # empty search.
        if real_failures:
            details = "; ".join(f"{name}: {provider_errors[name]}" for name in real_failures)
            notice = f"No articles found — one or more sources reported an issue ({details})."
        else:
            notice = "No articles found. Try a different keyword, language, or date range."

    return SearchResponse(
        articles=[
            ArticleOut(
                title=a.title,
                source_name=a.source_name,
                url=a.url,
                description=a.description,
                image_url=a.image_url,
                published_at=a.published_at,
                language=a.language,
                content=a.content,
            )
            for a in page_articles
        ],
        page=page,
        page_size=page_size,
        total_results=len(all_articles),
        has_more=has_more,
        provider_used=provider_used,
        keyword=keyword,
        language=language.value,
        newspaper=newspaper,
        edition=edition,
        date_filter=date_filter.value,
        notice=notice,
        from_cache=from_cache,
    )


@router.get("/tags", response_model=list[TagOut])
def list_tags(
    language: Language = Query(default=Language.en),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Predefined tags vary by language; custom tags don't (a person's own
    # tags stay visible no matter which search language they're using).
    predefined = [TagOut(id=None, tag=t, is_custom=False) for t in get_predefined_tags(language.value)]
    custom = [
        TagOut(id=row.id, tag=row.tag, is_custom=True)
        for row in tag_service.list_custom_tags(db, current_user.id)
    ]
    return predefined + custom


@router.post("/tags", response_model=TagOut, status_code=status.HTTP_201_CREATED)
def create_tag(
    payload: CreateTagRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = tag_service.add_custom_tag(db, current_user.id, payload.tag)
    return TagOut(id=row.id, tag=row.tag, is_custom=True)


@router.delete("/tags/{tag_id}", response_model=MessageResponse)
def delete_tag(
    tag_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tag_service.delete_custom_tag(db, current_user.id, tag_id)
    return MessageResponse(message="Tag deleted.")
