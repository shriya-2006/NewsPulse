"""
Health check route.

This is the ONLY functional endpoint on Day 1. Its sole purpose is to
prove the backend process is alive and reachable from the frontend.
"""

from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "message": "Backend Connected Successfully",
        "service": "NewsPulse API",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
