"""Browser API routes — remote browser session control."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.api.app import get_browser, get_config

logger = logging.getLogger(__name__)
router = APIRouter()


class BrowserLaunchRequest(BaseModel):
    profile_name: str = "default"
    portal: str = ""


class NavigateRequest(BaseModel):
    profile_name: str = "default"
    url: str


class ScreenshotResponse(BaseModel):
    path: str
    url: str
    timestamp: float


@router.get("/status")
async def browser_status():
    """Get browser status for all profiles."""
    mgr = get_browser()
    return {
        "active_profiles": mgr.list_profiles(),
        "profiles_count": len(mgr.list_profiles()),
    }


@router.post("/launch")
async def launch_browser(req: BrowserLaunchRequest):
    """Launch a browser for a portal."""
    mgr = get_browser()
    try:
        ctx = await mgr.launch_browser(req.profile_name)
        return {
            "status": "launched",
            "profile": req.profile_name,
            "pages": len(ctx.pages),
        }
    except Exception as e:
        raise HTTPException(500, f"Launch failed: {e}")


@router.post("/navigate")
async def navigate(req: NavigateRequest):
    """Navigate a browser to a URL."""
    mgr = get_browser()
    try:
        page = await mgr.get_page(req.profile_name, req.url)
        return {
            "status": "navigated",
            "url": page.url,
            "title": await page.title(),
        }
    except Exception as e:
        raise HTTPException(500, f"Navigation failed: {e}")


@router.get("/screenshot/{profile_name}")
async def take_screenshot(profile_name: str):
    """Take a screenshot of the current page."""
    mgr = get_browser()
    try:
        path = await mgr.take_screenshot(profile_name)
        return ScreenshotResponse(
            path=str(path),
            url="",
            timestamp=time.time(),
        )
    except Exception as e:
        raise HTTPException(500, f"Screenshot failed: {e}")


@router.post("/close/{profile_name}")
async def close_browser(profile_name: str):
    """Close a browser profile."""
    mgr = get_browser()
    try:
        await mgr.close_browser(profile_name)
        return {"status": "closed", "profile": profile_name}
    except Exception as e:
        raise HTTPException(500, f"Close failed: {e}")


@router.post("/close-all")
async def close_all():
    """Close all browsers."""
    mgr = get_browser()
    await mgr.close_all()
    return {"status": "all_closed"}
