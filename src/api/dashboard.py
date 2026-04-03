"""Dashboard API routes — analytics and stats."""

from __future__ import annotations

import logging
from fastapi import APIRouter
from src.api.app import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/stats")
async def get_stats():
    """Get dashboard statistics."""
    db = get_db()
    return db.application_stats()


@router.get("/applications")
async def list_applications(status: str = "", limit: int = 50, offset: int = 0):
    """List applications with optional status filter."""
    from src.core.models import ApplicationStatus
    db = get_db()
    status_enum = None
    if status:
        try:
            status_enum = ApplicationStatus(status)
        except ValueError:
            pass
    apps = db.list_applications(status=status_enum, limit=limit, offset=offset)
    return [
        {
            "id": app.id,
            "job_id": app.job_id,
            "status": app.status.value,
            "applied_date": app.applied_date.isoformat() if app.applied_date else None,
            "reference_id": app.reference_id,
            "notes": app.notes,
            "created_at": app.created_at.isoformat() if app.created_at else None,
        }
        for app in apps
    ]


@router.get("/deadlines")
async def upcoming_deadlines(days: int = 7):
    """Get jobs with upcoming deadlines."""
    db = get_db()
    jobs = db.upcoming_deadlines(days=days)
    return [
        {
            "id": j.id,
            "title": j.title,
            "portal": j.portal,
            "last_date": j.last_date.isoformat() if j.last_date else None,
            "url": j.url,
        }
        for j in jobs
    ]


@router.get("/recent-jobs")
async def recent_jobs(limit: int = 20):
    """Get recently discovered jobs."""
    db = get_db()
    jobs = db.search_jobs(limit=limit)
    return [
        {
            "id": j.id,
            "title": j.title,
            "portal": j.portal,
            "location": j.location,
            "salary": j.salary,
            "last_date": j.last_date.isoformat() if j.last_date else None,
            "match_score": j.match_score,
            "url": j.url,
        }
        for j in jobs
    ]
