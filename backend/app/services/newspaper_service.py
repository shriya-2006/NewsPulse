"""
Newspaper/edition business logic — everything here reads from (or, only
once, writes to) the `newspapers` and `newspaper_editions` tables. No
static Python dict is consulted at request time; that's the entire
point of this module existing.

Note on `languages`: these three (en/te/hi) are kept as a small fixed
list here rather than a database table on purpose. Unlike newspapers/
editions, adding a language isn't a pure data change — it also requires
RSS locale support, provider language capability flags, and translated
predefined tags (see app/utils/newspaper_sources.py), so it's reasonably
scoped as a backend-code change, not a runtime DB insert. It's still
served through a real endpoint (`GET /news/languages`) rather than
hardcoded in the frontend, satisfying the same "don't hardcode it on
the client" principle for the piece of this hierarchy where it applies.
"""

from sqlalchemy.orm import Session

from app.db.seed_data import LANGUAGE_SEED_DATA, NEWSPAPER_SEED_DATA
from app.models.newspaper import Newspaper, NewspaperEdition

_LANGUAGE_ALIASES = {
    "en": "en", "english": "en",
    "te": "te", "telugu": "te",
    "hi": "hi", "hindi": "hi",
}


def normalize_language(value: str) -> str | None:
    """Accepts a language code ('te') or display name ('Telugu'),
    case-insensitively. Returns the canonical code, or None if unrecognized."""
    return _LANGUAGE_ALIASES.get(value.strip().lower())


def list_languages() -> list[dict]:
    return LANGUAGE_SEED_DATA


def seed_if_empty(db: Session) -> None:
    """Populates newspapers/editions from seed_data.py exactly once —
    if the table already has rows (any prior seed, or manually-added
    newspapers), this is a complete no-op."""
    if db.query(Newspaper).first() is not None:
        return

    for entry in NEWSPAPER_SEED_DATA:
        newspaper = Newspaper(
            key=entry["key"],
            label=entry["label"],
            language=entry["language"],
            domain=entry["domain"],
            edition_query_supported=entry["edition_query_supported"],
        )
        db.add(newspaper)
        db.flush()  # assigns newspaper.id for the editions below

        for edition_name in entry["editions"]:
            db.add(NewspaperEdition(newspaper_id=newspaper.id, name=edition_name))

    db.commit()


def list_newspapers(db: Session, language_code: str | None = None) -> list[Newspaper]:
    query = db.query(Newspaper)
    if language_code:
        query = query.filter(Newspaper.language == language_code)
    return query.order_by(Newspaper.label).all()


def get_newspaper_by_key(db: Session, key: str) -> Newspaper | None:
    return db.query(Newspaper).filter(Newspaper.key == key).first()


def list_editions(db: Session, newspaper_key: str) -> list[str] | None:
    """Returns edition names for a newspaper, an empty list if it exists
    but has none, or None if the newspaper key doesn't exist at all —
    callers use None specifically to distinguish "unknown newspaper"
    (404) from "known newspaper, no editions yet" (200 with [])."""
    newspaper = get_newspaper_by_key(db, newspaper_key)
    if newspaper is None:
        return None
    return [e.name for e in newspaper.editions]


def list_all_editions(db: Session) -> list[str]:
    """
    Every distinct edition name across every newspaper, for when the
    person wants to filter by edition (e.g. "Visakhapatnam") without
    committing to one specific newspaper first.
    """
    rows = db.query(NewspaperEdition.name).distinct().order_by(NewspaperEdition.name).all()
    return [name for (name,) in rows]
