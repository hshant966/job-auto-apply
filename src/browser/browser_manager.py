"""Browser lifecycle manager — Playwright Chromium with stealth v3 and session persistence.

Integrates:
- Fingerprint profiles (consistent browser identity)
- TLS fingerprint spoofing (JA3/JA4 bypass)
- Comprehensive stealth patches (20+ detection vectors)
- Human-like interaction simulation
- Session persistence
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from pathlib import Path
from typing import Any, Optional

from playwright.async_api import async_playwright, BrowserContext, Page

from .navigation_helper import NavigationHelper
from .session_persistence import SessionPersistence
from .stealth import StealthManager
from .fingerprint_profiles import FingerprintProfileManager
from .tls_fingerprint import TLSFingerprintManager

logger = logging.getLogger(__name__)


class BrowserManager:
    """Manages Playwright browser contexts with per-portal persistence.

    Features:
    - Automatic fingerprint profile selection (consistent per-session)
    - TLS fingerprint normalization (Chrome JA3/JA4 matching)
    - 20+ stealth patches injected before page load
    - Human-like mouse/keyboard/scroll behavior
    - Session persistence and restoration
    """

    def __init__(self, config=None):
        from src.core.config import AppConfig
        from src.core.database import Database
        self.config = config or AppConfig.load()
        self._playwright = None
        self._contexts: dict[str, BrowserContext] = {}
        self._stealth = StealthManager()
        self._fingerprint_mgr = FingerprintProfileManager()
        self._tls_mgr: Optional[TLSFingerprintManager] = None
        self._db = Database(self.config.db_path)
        self._sessions = SessionPersistence(self._db)
        self._nav = NavigationHelper()
        self._data_dir = Path(self.config.browser.data_dir)
        self._screenshot_dir = Path(self.config.browser.screenshot_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._screenshot_dir.mkdir(parents=True, exist_ok=True)

        # Initialize TLS fingerprint manager
        try:
            self._tls_mgr = TLSFingerprintManager()
            logger.info("TLS fingerprint manager initialized")
        except Exception as e:
            logger.warning(f"TLS fingerprint manager init failed (non-fatal): {e}")

    async def _ensure_pw(self):
        if self._playwright is None:
            self._playwright = await async_playwright().start()
        return self._playwright

    async def launch(self, profile: str = "default", **kwargs) -> BrowserContext:
        """Launch or return existing browser context for a profile.

        Args:
            profile: Session profile name (used for data directory isolation)
            **kwargs: Override options (user_agent, viewport, headless, proxy, etc.)

        Returns:
            BrowserContext with full stealth patches applied
        """
        if profile in self._contexts:
            return self._contexts[profile]

        pw = await self._ensure_pw()
        profile_dir = self._data_dir / profile
        profile_dir.mkdir(parents=True, exist_ok=True)

        # ── Select fingerprint profile ──────────────────────────────────
        fp_profile = self._fingerprint_mgr.select_random()
        logger.info(f"Selected fingerprint profile: {fp_profile.name} ({fp_profile.description})")

        # Configure stealth manager with profile
        self._stealth.set_profile(fp_profile)
        if self._tls_mgr:
            self._stealth.set_tls_manager(self._tls_mgr)

        # ── Browser launch options ──────────────────────────────────────
        ua = kwargs.get("user_agent") or fp_profile.user_agent
        vp = kwargs.get("viewport") or (fp_profile.viewport.width, fp_profile.viewport.height)

        opts: dict[str, Any] = {
            "headless": kwargs.get("headless", self.config.browser.headless),
            "user_data_dir": str(profile_dir),
            "viewport": {"width": vp[0], "height": vp[1]},
            "user_agent": ua,
            "ignore_https_errors": kwargs.get("ignore_https_errors", True),
            "java_script_enabled": True,
            "bypass_csp": kwargs.get("bypass_csp", True),
            "locale": kwargs.get("locale", fp_profile.locale),
            "timezone_id": kwargs.get("timezone_id", fp_profile.timezone),
            # Additional anti-detection args
            "args": kwargs.get("args", []) + [
                "--disable-blink-features=AutomationControlled",
                "--disable-features=Translate",
                "--disable-default-apps",
                "--disable-component-extensions-with-background-pages",
                "--disable-background-networking",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--disable-dev-shm-usage",
                "--no-first-run",
                "--no-default-browser-check",
                "--password-store=basic",
                "--use-mock-keychain",
                "--disable-ipc-flooding-protection",
            ],
        }

        proxy = kwargs.get("proxy")
        if proxy:
            opts["proxy"] = proxy

        ctx = await pw.chromium.launch_persistent_context(str(profile_dir), **opts)

        # ── Apply TLS fingerprint to context ────────────────────────────
        if self._tls_mgr:
            try:
                await self._tls_mgr.apply_to_context(ctx)
                logger.debug("TLS fingerprint patches applied to context")
            except Exception as e:
                logger.warning(f"TLS patch application failed (non-fatal): {e}")

        # ── Apply stealth to all existing pages ─────────────────────────
        if self.config.browser.stealth_enabled:
            for page in ctx.pages:
                await self._stealth.apply(page)
            # Apply stealth to any new pages opened during the session
            ctx.on("page", lambda p: asyncio.ensure_future(self._stealth.apply(p)))

        # ── Resource blocking for speed (keep CSS for layout) ───────────
        blocked = {"font", "media"}
        # Only block images on headless — real browsers show images
        if opts.get("headless", self.config.browser.headless):
            blocked.add("image")

        async def _route_handler(route):
            rt = route.request.resource_type
            # Block heavy resources but allow CSS/JS/Document/XHR/Fetch
            if rt in blocked:
                await route.abort()
            else:
                await route.continue_()

        await ctx.route("**/*", _route_handler)

        # ── Restore session cookies ─────────────────────────────────────
        try:
            session = await self._sessions.restore_session(profile)
            if session and session.get("cookies"):
                await ctx.add_cookies(session["cookies"])
        except Exception:
            pass

        self._contexts[profile] = ctx
        logger.info(
            f"Browser launched: profile={profile}, "
            f"fp={fp_profile.name}, headless={opts['headless']}, "
            f"stealth={self.config.browser.stealth_enabled}, "
            f"viewport={vp}"
        )
        return ctx

    async def get_page(self, profile: str = "default", url: str = "") -> Page:
        """Get or create a page in the specified profile context."""
        ctx = await self.launch(profile)
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        if url:
            await page.goto(url, wait_until="domcontentloaded")
        return page

    async def screenshot(self, profile: str = "default", name: str = "screenshot") -> str:
        """Take a screenshot and save it."""
        page = await self.get_page(profile)
        ts = int(time.time())
        path = self._screenshot_dir / f"{profile}_{name}_{ts}.png"
        await page.screenshot(path=str(path), full_page=False)
        logger.info(f"Screenshot: {path}")
        return str(path)

    async def screenshot_bytes(self, profile: str = "default") -> bytes:
        """Take a screenshot and return raw bytes."""
        page = await self.get_page(profile)
        return await page.screenshot(type="png")

    async def save_session(self, profile: str):
        """Save the current session state (cookies, etc.)."""
        ctx = self._contexts.get(profile)
        if not ctx:
            return
        try:
            await self._sessions.save_session(profile, ctx)
        except Exception as e:
            logger.warning(f"Session save failed: {e}")

    async def close(self, profile: str):
        """Close a specific profile's browser context."""
        ctx = self._contexts.pop(profile, None)
        if ctx:
            await self.save_session(profile)
            await ctx.close()

    async def close_all(self):
        """Close all browser contexts and stop Playwright."""
        for name in list(self._contexts.keys()):
            await self.close(name)
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    def list_profiles(self) -> list[str]:
        """List currently active browser profiles."""
        return list(self._contexts.keys())

    async def navigate(self, profile: str, url: str) -> Page:
        """Navigate to a URL with safe navigation handling."""
        page = await self.get_page(profile)
        await self._nav.safe_goto(page, url)
        return page

    async def human_click(self, page: Page, selector: str) -> bool:
        """Click an element with full human-like behavior.

        Combines curved mouse movement, thinking delays, and natural timing.
        """
        return await self._stealth.human_click(page, selector)

    async def human_type(self, page: Page, selector: str, text: str):
        """Type text with human-like speed, mistakes, and corrections."""
        await self._stealth.human_type(page, selector, text)

    @property
    def navigation(self) -> NavigationHelper:
        """Access the shared NavigationHelper instance."""
        return self._nav

    @property
    def sessions(self) -> SessionPersistence:
        """Access the shared SessionPersistence instance."""
        return self._sessions

    @property
    def stealth(self) -> StealthManager:
        """Access the StealthManager instance."""
        return self._stealth

    @property
    def fingerprint(self) -> FingerprintProfileManager:
        """Access the FingerprintProfileManager instance."""
        return self._fingerprint_mgr

    async def handle_popups(self, page: Page) -> int:
        """Convenience: close popups on *page* via NavigationHelper."""
        return await self._nav.handle_popups(page)
