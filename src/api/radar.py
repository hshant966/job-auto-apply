"""Radar scanner API — trigger scans and list sources."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.api.app import get_db, get_config

logger = logging.getLogger(__name__)
router = APIRouter()


class ScanRequest(BaseModel):
    """Optional scan parameters."""
    profile: Optional[dict[str, Any]] = None
    rss_feeds: Optional[dict[str, str]] = None


@router.post("/scan")
async def trigger_scan(req: ScanRequest = ScanRequest()):
    """Trigger a radar scan across all configured sources.

    Accepts optional profile dict for targeted scanning and
    optional custom RSS feeds dict.
    """
    from src.ai.radar_scanner import RadarScanner

    db = get_db()
    scanner = RadarScanner(db=db, rss_feeds=req.rss_feeds)

    try:
        result = await asyncio.to_thread(
            scanner.scan_all_sources,
            profile=req.profile,
        )
    except Exception as e:
        logger.error("Radar scan failed: %s", e)
        raise HTTPException(500, f"Scan failed: {e}")

    return {
        "status": "ok",
        "total_found": result.total_found,
        "new_jobs": len(result.new_jobs),
        "duplicates_removed": result.duplicates_removed,
        "sources_scanned": result.sources_scanned,
        "duration_seconds": result.scan_duration_seconds,
        "timestamp": result.timestamp,
        "errors": result.errors,
        "jobs": result.new_jobs[:50],  # cap response size
    }


@router.get("/sources")
async def list_sources():
    """List configured radar scan sources (RSS feeds)."""
    from src.ai.radar_scanner import RadarScanner, DEFAULT_RSS_FEEDS

    db = get_db()
    scanner = RadarScanner(db=db)
    return {
        "rss_feeds": scanner.sources,
        "total": len(scanner.sources),
    }
