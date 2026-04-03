"""Naukri Adapter — India's largest job portal."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Optional

from .base_adapter import BaseAdapter, FormField, ApplyResult

logger = logging.getLogger(__name__)


class NaukriAdapter(BaseAdapter):
    """Adapter for Naukri.com job search and application."""

    portal_name = "naukri"
    portal_url = "https://www.naukri.com"

    async def login(self, browser_context) -> bool:
        """Login to Naukri via persistent session."""
        try:
            page = await browser_context.new_page()
            await page.goto(self.portal_url, wait_until="domcontentloaded")
            await self._human_delay(2, 4)

            # Check if already logged in
            profile_link = page.locator("a[href*='mnjuser'], .nI-gNb-drawer-open")
            if await profile_link.count() > 0:
                logger.info("Naukri: Already logged in")
                return True

            credentials = self.config.get_portal_credentials("naukri")
            if not credentials:
                logger.error("No Naukri credentials configured")
                return False

            # Click login
            login_btn = page.locator("a[href*='login'], button:has-text('Login')").first
            if await login_btn.count() > 0:
                await login_btn.click()
                await self._human_delay(2, 4)

            await self._human_type(page, "input[type='email'], #usernameField", credentials["username"])
            await self._human_delay(0.5, 1.5)
            await self._human_type(page, "input[type='password'], #passwordField", credentials["password"])
            await self._human_delay(1, 2)

            await page.click("button[type='submit'], .loginButton")
            await self._human_delay(3, 6)

            logger.info("Naukri login attempted")
            return True

        except Exception as e:
            logger.error(f"Naukri login error: {e}")
            return False

    async def search_jobs(self, filters: dict) -> list:
        """Search Naukri jobs."""
        from src.core.models import Job
        jobs = []
        try:
            page = await self._get_page()

            keywords = filters.get("keywords", "software engineer")
            location = filters.get("location", "")
            experience = filters.get("experience", "")

            # Build search URL
            search_slug = keywords.lower().replace(" ", "-")
            url = f"{self.portal_url}/{search_slug}-jobs"
            if location:
                url += f"-in-{location.lower().replace(' ', '-')}"

            params = []
            if experience:
                params.append(f"experience={experience}")
            if params:
                url += "?" + "&".join(params)

            await page.goto(url, wait_until="domcontentloaded")
            await self._human_delay(3, 5)

            # Scroll to load more
            for _ in range(3):
                await page.evaluate("window.scrollBy(0, 1000)")
                await self._human_delay(1, 2)

            # Extract job cards
            cards = page.locator(".srp-jobtuple-wrapper, .jobTuple")
            count = await cards.count()

            for i in range(min(count, 25)):
                try:
                    card = cards.nth(i)
                    title_el = card.locator(".title, a.title").first
                    company_el = card.locator(".comp-name, .subTitle").first
                    exp_el = card.locator(".expwdth, .experience").first
                    loc_el = card.locator(".locWdth, .location").first
                    salary_el = card.locator(".sal, .salary").first

                    title = await title_el.text_content() if await title_el.count() > 0 else ""
                    href = await title_el.get_attribute("href") if await title_el.count() > 0 else ""
                    company = await company_el.text_content() if await company_el.count() > 0 else ""
                    exp = await exp_el.text_content() if await exp_el.count() > 0 else ""
                    loc = await loc_el.text_content() if await loc_el.count() > 0 else ""
                    salary = await salary_el.text_content() if await salary_el.count() > 0 else ""

                    if title and len(title.strip()) > 3:
                        jobs.append(Job(
                            title=title.strip(),
                            portal="naukri",
                            url=href or "",
                            department=company.strip() if company else "",
                            location=loc.strip() if loc else "",
                            salary=salary.strip() if salary else "",
                            description=f"Naukri job: {title.strip()} | Exp: {exp.strip()}",
                        ))

                except Exception:
                    continue

            logger.info(f"Naukri: Found {len(jobs)} jobs")

        except Exception as e:
            logger.error(f"Naukri search error: {e}")

        return jobs

    async def get_application_form(self, page, job_url: str) -> list[FormField]:
        """Naukri uses stored profile — minimal form filling."""
        return []

    async def fill_application(self, page, profile_data: dict) -> bool:
        """Naukri applies with stored profile."""
        return True

    async def upload_documents(self, page, documents: dict) -> bool:
        """Naukri uses stored resume."""
        return True

    async def submit_application(self, page) -> Optional[str]:
        """Click Apply on Naukri."""
        try:
            apply_btn = page.locator("button:has-text('Apply'), .apply-button, a:has-text('Apply')").first
            if await apply_btn.count() > 0:
                await self._human_delay(1, 3)
                await apply_btn.click()
                await self._human_delay(3, 5)

                # Check for success
                success = page.locator(".apply-success, .applied-message, .already-applied")
                if await success.count() > 0:
                    logger.info("Naukri: Application successful")
                    return "naukri_applied"

                return "submitted"

            return None

        except Exception as e:
            logger.error(f"Naukri apply error: {e}")
            return None
