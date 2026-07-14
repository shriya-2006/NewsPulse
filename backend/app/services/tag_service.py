"""
Tag business logic: predefined industry tags (static, shared by everyone)
plus per-user custom tags stored in MySQL.
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.tag import CustomTag
from app.utils.newspaper_sources import all_predefined_tags

MAX_TAG_LENGTH = 100


def list_custom_tags(db: Session, user_id: int) -> list[CustomTag]:
    return (
        db.query(CustomTag)
        .filter(CustomTag.user_id == user_id)
        .order_by(CustomTag.created_at.desc())
        .all()
    )


def add_custom_tag(db: Session, user_id: int, tag: str) -> CustomTag:
    cleaned = tag.strip()
    if not cleaned:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Tag cannot be blank.")
    if len(cleaned) > MAX_TAG_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Tag must be {MAX_TAG_LENGTH} characters or fewer.",
        )

    # Don't let someone re-add a predefined tag as a "custom" one, and
    # don't let the same user add the same custom tag twice.
    if cleaned.lower() in {t.lower() for t in all_predefined_tags()}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This is already one of the predefined tags.",
        )
    existing = (
        db.query(CustomTag)
        .filter(CustomTag.user_id == user_id, CustomTag.tag.ilike(cleaned))
        .first()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You already added this tag.")

    row = CustomTag(user_id=user_id, tag=cleaned)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete_custom_tag(db: Session, user_id: int, tag_id: int) -> None:
    row = (
        db.query(CustomTag)
        .filter(CustomTag.id == tag_id, CustomTag.user_id == user_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found.")
    db.delete(row)
    db.commit()
