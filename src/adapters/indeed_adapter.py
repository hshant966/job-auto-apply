"""Indeed India Adapter."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Optional

from .base_adapter import BaseAdapter, FormField, ApplyResult

logger = logging.getLogger(__name__)


class IndeedAdapter(BaseAdapter):
    """Adapter for Indeed India job search and application."""

    portal_name = "indeed"
    portal_url = "https://www.indeed.co.in"

    async def login(self, browser_context) -> bool:
        try:
            page = await browser_context.new_page()
            await page.goto(f"{self.portal_url}/login", wait_until="domcontentloaded")
            await self._human_delay(2, 4)

            credentials = self.config.get_portal_credentials("indeed")
            if not credentials:
                logger.error("No Indeed credentials configured")
                return False

            await self._human_type(page, "input[type='email'], #ifl-InputFormField-3", credentials["username"])
            await self._human_delay(0.5, 1)
            await page.click("button[type='submit']")
            await self._human_delay(2, 4)

            await self._human_type(page, "input[type='password'], #ifl-InputFormField-5", credentials["password"])
            await self._human_delay(0.5, 1)
            await page.click("button[type='submit']")
            await self._human_delay(3, 5)

            logger.info("Indeed login attempted")
            return True

        except Exception as e:
            logger.error(f"Indeed login error: {e}")
            return False

    async def search_jobs(self, filters: dict) -> list:
        from src.core.models import Job
        jobs = []
        try:
            page = await self._get_page()
            keywords = filters.get("keywords", "")
            location = filters.get("location", "India")

            url = f"{self.portal_url}/jobs?q={keywords}&l={location}"
            await page.goto(url, wait_until="domcontentloaded")
            await self._human_delay(3, 5)

            cards = page.locator(".job_seen_beacon, .resultContent, .jobsearch-ResultsList > li")
            count = await cards.count()

            for i in range(min(count, 20)):
                try:
                    card = cards.nth(i)
                    title_el = card.locator("h2 a, .jcs-JobTitle a, a[data-jk]").first
                    company_el = card.locator(".companyName, [data-testid='company-name']").first
                    loc_el = card.locator(".companyLocation, [data-testid='text-location']").first

                    title = await title_el.text_content() if await title_el.count() > 0 else ""
                    href = await title_el.get_attribute("href") if await title_el.count() > 0 else ""
                    company = await company_el.text_content() if await company_el.count() > 0 else ""
                    loc = await loc_el.text_content() if await loc_el.count() > 0 else ""

                    if title:
                        full_url = f"{self.portal_url}{href}" if href and not href.startswith("http") else href
                        jobs.append(Job(
                            title=title.strip(),
                            portal="indeed",
                            url=full_url or "",
                            department=company.strip() if company else "",
                            location=loc.strip() if loc else "",
                        ))

                except Exception:
                    continue

            logger.info(f"Indeed: Found {len(jobs)} jobs")

        except Exception as e:
            logger.error(f"Indeed search error: {e}")

        return jobs

    async def get_application_form(self, page, job_url: str) -> list[FormField]:
        return []

    async def fill_application(self, page, profile_data: dict) -> bool:
        return True

    async def upload_documents(self, page, documents: dict) -> bool:
        try:
            resume = documents.get("resume")
            if resume:
                upload = page.locator("input[type='file']").first
                if await upload.count() > 0:
                    await upload.set_input_files(resume)
                    await self._human_delay(1, 2)
            return True
        except Exception:
            return False

    async def submit_application(self, page) -> Optional[str]:
        try:
            apply_btn = page.locator("button:has-text('Apply'), .ia-IndeedApplyButton").first
            if await apply_btn.count() > 0:
                await self._human_delay(1, 3)
                await apply_btn.click()
                await self._human_delay(3, 5)
                return "indeed_applied"
            return None
        except Exception as e:
            logger.error(f"Indeed apply error: {e}")
            return None
