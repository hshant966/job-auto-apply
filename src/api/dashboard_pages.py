"""Dashboard HTML routes — serves the web UI."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.api.app import get_db

logger = logging.getLogger(__name__)
html_router = APIRouter()

templates_dir = Path(__file__).resolve().parent.parent / "dashboard" / "templates"
templates_dir.mkdir(parents=True, exist_ok=True)
templates = Jinja2Templates(directory=str(templates_dir))


@html_router.get("/", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Main dashboard page."""
    db = get_db()
    stats = db.application_stats()
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "stats": stats,
    })


@html_router.get("/jobs", response_class=HTMLResponse)
async def jobs_page(request: Request):
    """Jobs listing page."""
    return templates.TemplateResponse("jobs.html", {"request": request})


@html_router.get("/applications", response_class=HTMLResponse)
async def applications_page(request: Request):
    """Applications tracker page."""
    return templates.TemplateResponse("applications.html", {"request": request})


@html_router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    """Profile management page."""
    return templates.TemplateResponse("profile.html", {"request": request})


@html_router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Settings page."""
    return templates.TemplateResponse("settings.html", {"request": request})
