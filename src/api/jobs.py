"""Job discovery, search, and filtering API."""
from __future__ import annotations
import asyncio
import logging
from fastapi import APIRouter, HTTPException, Query
from src.api.app import get_db, get_config
from src.core.models import Job

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
async def list_jobs(
    portal: str = "", location: str = "",
    limit: int = Query(50, le=200), offset: int = 0,
):
    """List/search jobs with filters."""
    db = get_db()
    jobs = db.search_jobs(portal=portal, location=location, limit=limit, offset=offset)
    return {
        "jobs": [j.model_dump(mode="json") for j in jobs],
        "total": db.count_jobs(),
        "limit": limit, "offset": offset,
    }


@router.get("/{job_id}")
async def get_job(job_id: int):
    """Get a single job by ID."""
    db = get_db()
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    # Check if already applied
    app = db.get_application_by_job(job_id)
    return {
        "job": job.model_dump(mode="json"),
        "application": app.model_dump(mode="json") if app else None,
    }


@router.post("/scan")
async def trigger_scan():
    """Trigger a job scan across all portals."""
    from src.adapters.ssc_adapter import SSCAdapter
    from src.adapters.upsc_adapter import UPSCAdapter
    from src.adapters.indeed_adapter import IndeedAdapter

    db = get_db()
    config = get_config()
    adapters = [SSCAdapter(config), UPSCAdapter(config), IndeedAdapter(config)]

    all_jobs = []
    for adapter in adapters:
        try:
            jobs = await adapter.search_jobs({})
            all_jobs.extend(jobs)
        except Exception as e:
            logger.warning(f"Scan error for {adapter.portal_name}: {e}")

    # Also scan RSS feeds
    try:
        import feedparser
        for feed_url in config.scan.rss_feeds:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:50]:
                    all_jobs.append(Job(
                        title=entry.get("title", ""),
                        portal="rss",
                        url=entry.get("link", ""),
                        description=entry.get("summary", ""),
                    ))
            except Exception:
                pass
    except ImportError:
        pass

    # Save unique jobs
    saved = 0
    for job in all_jobs:
        if job.title and job.url:
            db.save_job(job)
            saved += 1

    return {"scanned": len(all_jobs), "saved": saved}


@router.get("/upcoming/deadlines")
async def upcoming_deadlines(days: int = Query(7, le=30)):
    """Get jobs with upcoming deadlines."""
    db = get_db()
    jobs = db.upcoming_deadlines(days)
    return {"jobs": [j.model_dump(mode="json") for j in jobs], "count": len(jobs)}
