"""Smart page navigation — retry logic, popup handling, redirect detection."""

from __future__ import annotations

import asyncio
import logging
import random
import re
from typing import Callable, Optional, Union

from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)


class NavigationHelper:
    """Robust navigation utilities for browser automation.

    Ported from V1 with identical behaviour.  Stateless — safe to share
    across profiles.
    """

    # Common popup / modal / overlay selectors
    POPUP_SELECTORS = [
        # Cookie consent
        '[class*="cookie"] button',
        '[id*="cookie"] button',
        '[class*="consent"] button',
        'button[class*="accept"]',
        # Newsletter / signup modals
        '[class*="modal"] [class*="close"]',
        '[class*="popup"] [class*="close"]',
        '[class*="overlay"] [class*="close"]',
        '[role="dialog"] [aria-label="Close"]',
        '[role="dialog"] button[class*="close"]',
        # Notification permission popups
        '[class*="notification"] [class*="dismiss"]',
        # Generic close buttons
        '.modal .close',
        '.popup .close',
        '.overlay .close',
        'button[aria-label="Close"]',
        'button[aria-label="close"]',
        'button[aria-label="Dismiss"]',
        # Job-portal specifics
        '[data-testid="close-button"]',
        '[class*="dismiss"]',
        '.modal-close',
    ]

    def __init__(
        self,
        default_timeout: int = 30_000,
        max_retries: int = 3,
    ) -> None:
        self._default_timeout = default_timeout
        self._max_retries = max_retries

    # ── Core navigation ──────────────────────────────────────────────

    async def safe_goto(
        self,
        page: Page,
        url: str,
        wait_for: str = "networkidle",
        timeout: Optional[int] = None,
    ) -> bool:
        """Navigate to *url* with error handling.

        *wait_for* can be ``"networkidle"``, ``"load"``, ``"domcontentloaded"``,
        or a CSS selector to wait for after load.
        """
        timeout = timeout or self._default_timeout
        try:
            logger.info("Navigating to: %s", url)
            if wait_for in ("networkidle", "load", "domcontentloaded"):
                await page.goto(url, wait_until=wait_for, timeout=timeout)
            else:
                await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
                await page.wait_for_selector(wait_for, timeout=timeout)

            await asyncio.sleep(random.uniform(0.5, 1.5))
            logger.info("Loaded: %s", url)
            return True
        except PlaywrightTimeout:
            logger.warning("Timeout navigating to %s (%d ms)", url, timeout)
            return False
        except Exception as exc:
            logger.error("Navigation error for %s: %s", url, exc)
            return False

    async def retry_navigation(
        self,
        page: Page,
        url: str,
        max_attempts: Optional[int] = None,
        wait_for: str = "networkidle",
        timeout: Optional[int] = None,
    ) -> bool:
        """Navigate with exponential-backoff retry on failure."""
        max_attempts = max_attempts or self._max_retries
        for attempt in range(max_attempts):
            if await self.safe_goto(page, url, wait_for=wait_for, timeout=timeout):
                if attempt:
                    logger.info("Navigation succeeded on attempt %d", attempt + 1)
                return True
            if attempt < max_attempts - 1:
                backoff = 2 ** attempt + random.uniform(0.5, 1.5)
                logger.info(
                    "Retrying in %.1fs (attempt %d/%d)", backoff, attempt + 2, max_attempts
                )
                await asyncio.sleep(backoff)
        logger.error("All %d attempts failed for %s", max_attempts, url)
        return False

    # ── Element interaction ──────────────────────────────────────────

    async def wait_and_click(
        self,
        page: Page,
        selector: str,
        timeout: Optional[int] = None,
        retries: int = 1,
    ) -> bool:
        """Wait for *selector* visible then click. Returns success."""
        timeout = timeout or self._default_timeout
        for attempt in range(retries):
            try:
                loc = page.locator(selector)
                await loc.wait_for(state="visible", timeout=timeout)
                await asyncio.sleep(random.uniform(0.2, 0.5))
                await loc.click(timeout=timeout)
                logger.debug("Clicked: %s", selector)
                return True
            except PlaywrightTimeout:
                logger.warning("Timeout waiting for %s (%d/%d)", selector, attempt + 1, retries)
            except Exception as exc:
                logger.warning("Click failed %s (%d/%d): %s", selector, attempt + 1, retries, exc)
                if attempt < retries - 1:
                    await asyncio.sleep(random.uniform(0.5, 1.0))
        return False

    # ── Smart wait ───────────────────────────────────────────────────

    async def smart_wait(
        self,
        page: Page,
        condition: Union[str, Callable],
        timeout: Optional[int] = None,
    ) -> bool:
        """Wait for a CSS selector, URL pattern, or async predicate."""
        timeout = timeout or self._default_timeout
        try:
            if callable(condition):
                start = asyncio.get_event_loop().time()
                while (asyncio.get_event_loop().time() - start) * 1000 < timeout:
                    if await condition(page):
                        return True
                    await asyncio.sleep(0.5)
                return False

            if isinstance(condition, str):
                if not condition.startswith(("http", "/")):
                    await page.wait_for_selector(condition, state="visible", timeout=timeout)
                    return True
                await page.wait_for_url(condition, timeout=timeout)
                return True
        except PlaywrightTimeout:
            logger.warning("Smart wait timed out: %s", condition)
        except Exception as exc:
            logger.error("Smart wait error: %s", exc)
        return False

    # ── Popup handling ───────────────────────────────────────────────

    async def handle_popups(self, page: Page) -> int:
        """Auto-detect and close popups / modals / overlays.

        Returns the number of popups closed.
        """
        closed = 0
        for selector in self.POPUP_SELECTORS:
            try:
                for el in await page.locator(selector).all():
                    if await el.is_visible():
                        await el.click(timeout=3000)
                        closed += 1
                        await asyncio.sleep(random.uniform(0.3, 0.7))
                        logger.debug("Closed popup: %s", selector)
            except Exception:
                pass

        # Absorb any JS alert/confirm dialogs
        try:
            page.on("dialog", lambda d: d.accept())
        except Exception:
            pass

        if closed:
            logger.info("Closed %d popup(s)", closed)
        return closed

    # ── Redirect detection ───────────────────────────────────────────

    async def handle_redirect(
        self,
        page: Page,
        expected_url: str,
        timeout: Optional[int] = None,
    ) -> bool:
        """Wait for the page to land on *expected_url* (supports ``*`` wildcards)."""
        timeout = timeout or self._default_timeout
        try:
            if "*" in expected_url:
                pattern = expected_url.replace("*", ".*")
                await page.wait_for_url(re.compile(pattern), timeout=timeout)
            else:
                await page.wait_for_url(expected_url, timeout=timeout)
            logger.debug("Redirect complete: %s", page.url)
            return True
        except PlaywrightTimeout:
            logger.warning("Redirect timeout — expected %s, current %s", expected_url, page.url)
            return False

    # ── Page readiness ───────────────────────────────────────────────

    async def wait_for_page_ready(
        self,
        page: Page,
        timeout: Optional[int] = None,
    ) -> bool:
        """Wait for network idle + loading indicators to disappear."""
        timeout = timeout or self._default_timeout
        try:
            await page.wait_for_load_state("networkidle", timeout=timeout)
            for sel in (
                '[class*="loading"]',
                '[class*="spinner"]',
                '[class*="loader"]',
                '[aria-busy="true"]',
                ".preloader",
            ):
                try:
                    await page.wait_for_selector(sel, state="hidden", timeout=2000)
                except Exception:
                    pass
            return True
        except Exception as exc:
            logger.warning("Page ready check failed: %s", exc)
            return False

    # ── Scrolling ────────────────────────────────────────────────────

    async def scroll_to_bottom(
        self,
        page: Page,
        step_size: int = 300,
        delay_ms: int = 200,
    ) -> None:
        """Smoothly scroll to the bottom of the page."""
        try:
            prev = 0
            while True:
                height = await page.evaluate("document.body.scrollHeight")
                if height == prev:
                    break
                prev = height
                await page.evaluate(f"window.scrollBy(0, {step_size})")
                await asyncio.sleep(delay_ms / 1000 * random.uniform(0.8, 1.2))
            logger.debug("Scrolled to bottom")
        except Exception as exc:
            logger.warning("Scroll failed: %s", exc)
