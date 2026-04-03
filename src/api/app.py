"""JobAutoApply — FastAPI Application with all routes."""

from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.config import AppConfig
from src.core.database import Database
from src.browser.browser_manager import BrowserManager

logger = logging.getLogger(__name__)

# Globals
config: AppConfig = None  # type: ignore
db: Database = None  # type: ignore
browser_mgr: BrowserManager = None  # type: ignore


def get_config() -> AppConfig:
    return config

def get_db() -> Database:
    return db

def get_browser() -> BrowserManager:
    return browser_mgr


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle."""
    global config, db, browser_mgr
    config = AppConfig.load()
    db = Database(config.db_path)
    browser_mgr = BrowserManager(config)

    # Create default profile if none exists
    if not db.get_profile(1):
        from src.core.models import UserProfile
        db.create_profile(UserProfile(), "default")

    logger.info("JobAutoApply started")
    yield

    # Cleanup
    await browser_mgr.close_all()
    db.close()
    logger.info("JobAutoApply stopped")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="JobAutoApply",
        description="AI-Powered Job Application Automation for India",
        version="2.0.0",
        lifespan=lifespan,
    )

    # Mount static files
    static_dir = Path(__file__).resolve().parent.parent / "dashboard" / "static"
    templates_dir = Path(__file__).resolve().parent.parent / "dashboard" / "templates"
    static_dir.mkdir(parents=True, exist_ok=True)
    templates_dir.mkdir(parents=True, exist_ok=True)

    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Register API routes
    from src.api import auth, profile as profile_routes, jobs as jobs_routes
    from src.api import apply as apply_routes, browser as browser_routes
    from src.api import ai as ai_routes, dashboard as dash_routes
    from src.api import portals as portal_routes, settings as settings_routes
    from src.api import resume as resume_routes
    from src.api import learning as learning_routes
    from src.api import radar as radar_routes
    from src.api import orchestrate as orchestrate_routes

    app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
    app.include_router(profile_routes.router, prefix="/api/profile", tags=["profile"])
    app.include_router(jobs_routes.router, prefix="/api/jobs", tags=["jobs"])
    app.include_router(apply_routes.router, prefix="/api/apply", tags=["apply"])
    app.include_router(browser_routes.router, prefix="/api/browser", tags=["browser"])
    app.include_router(ai_routes.router, prefix="/api/ai", tags=["ai"])
    app.include_router(dash_routes.router, prefix="/api/dashboard", tags=["dashboard"])
    app.include_router(portal_routes.router, prefix="/api/portals", tags=["portals"])
    app.include_router(settings_routes.router, prefix="/api/settings", tags=["settings"])
    app.include_router(resume_routes.router, prefix="/api/resume", tags=["resume"])
    app.include_router(learning_routes.router, prefix="/api/learning", tags=["learning"])
    app.include_router(radar_routes.router, prefix="/api/radar", tags=["radar"])
    app.include_router(orchestrate_routes.router, prefix="/api/orchestrate", tags=["orchestrate"])

    # Dashboard HTML routes
    from src.api.dashboard_pages import html_router
    app.include_router(html_router, tags=["html"])

    # Register auth middleware (must be after routes so exempt paths are checked at request time)
    from src.api.auth import register_auth_middleware
    register_auth_middleware(app)

    return app
