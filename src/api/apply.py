"""Application submission & tracking API."""
from __future__ import annotations
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException
from src.api.app import get_db
from src.core.models import ApplicationStatus

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
async def list_applications(status: str = "", limit: int = 50, offset: int = 0):
    """List all applications."""
    db = get_db()
    status_enum = None
    if status:
        try:
            status_enum = ApplicationStatus(status)
        except ValueError:
            pass
    apps = db.list_applications(status=status_enum, limit=limit, offset=offset)
    result = []
    for a in apps:
        d = a.model_dump(mode="json")
        d["job"] = db.get_job(a.job_id).model_dump(mode="json") if db.get_job(a.job_id) else None
        result.append(d)
    return {"applications": result, "total": len(result)}


@router.get("/{app_id}")
async def get_application(app_id: int):
    """Get application details."""
    db = get_db()
    app = db.get_application(app_id)
    if not app:
        raise HTTPException(404, "Application not found")
    job = db.get_job(app.job_id)
    return {
        "application": app.model_dump(mode="json"),
        "job": job.model_dump(mode="json") if job else None,
    }


@router.post("/create/{job_id}")
async def create_application(job_id: int):
    """Create a new application for a job."""
    db = get_db()
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    # Check if already applied
    existing = db.get_application_by_job(job_id)
    if existing and existing.status in (ApplicationStatus.SUBMITTED, ApplicationStatus.CONFIRMED):
        return {"message": "Already applied", "application_id": existing.id}
    app_id = db.create_application(job_id, ApplicationStatus.DRAFT)
    return {"application_id": app_id, "status": "draft"}


@router.post("/{app_id}/status")
async def update_status(app_id: int, status: str, reference_id: str = "", notes: str = ""):
    """Update application status."""
    db = get_db()
    try:
        status_enum = ApplicationStatus(status)
    except ValueError:
        raise HTTPException(400, f"Invalid status: {status}")
    ok = db.update_application_status(app_id, status_enum, reference_id, notes)
    if not ok:
        raise HTTPException(404, "Application not found")
    return {"ok": True, "status": status}


@router.post("/{app_id}/apply")
async def apply_to_job(app_id: int):
    """Trigger browser-based auto-apply for an application."""
    db = get_db()
    app = db.get_application(app_id)
    if not app:
        raise HTTPException(404, "Application not found")
    job = db.get_job(app.job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    # Update status to applying
    db.update_application_status(app_id, ApplicationStatus.APPLYING)

    # Return job info for browser automation
    return {
        "message": "Ready to apply",
        "job": job.model_dump(mode="json"),
        "portal": job.portal,
        "url": job.url,
    }
