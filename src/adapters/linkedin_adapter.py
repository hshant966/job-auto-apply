"""LinkedIn Adapter — Job search and Easy Apply automation."""

from __future__ import annotations

import logging
import random
from datetime import datetime
from typing import Any, Optional

from .base_adapter import BaseAdapter, FormField, ApplyResult

logger = logging.getLogger(__name__)


class LinkedInAdapter(BaseAdapter):
    """Adapter for LinkedIn job search and Easy Apply."""

    portal_name = "linkedin"
    portal_url = "https://www.linkedin.com"

    JOBS_URL = "https://www.linkedin.com/jobs/search/"
    FEED_URL = "https://www.linkedin.com/feed/"

    async def login(self, browser_context) -> bool:
        """Login to LinkedIn via persistent session."""
        try:
            page = await browser_context.new_page()
            await page.goto(self.FEED_URL, wait_until="domcontentloaded")
            await self._human_delay(3, 6)

            # Check if already logged in (persistent session)
            if "feed" in page.url.lower() and "login" not in page.url.lower():
                logger.info("LinkedIn: Already logged in (persistent session)")
                return True

            # Need to login
            credentials = self.config.get_portal_credentials("linkedin")
            if not credentials:
                logger.error("No LinkedIn credentials configured")
                return False

            await page.goto(f"{self.portal_url}/login", wait_until="domcontentloaded")
            await self._human_delay(2, 4)

            await self._human_type(page, "#username", credentials["username"])
            await self._human_delay(1, 2)
            await self._human_type(page, "#password", credentials["password"])
            await self._human_delay(1, 3)

            await page.click("button[type='submit']")
            await self._human_delay(4, 8)

            # Verify login
            if "feed" in page.url.lower() or "mynetwork" in page.url.lower():
                logger.info("LinkedIn login successful")
                return True

            logger.warning("LinkedIn login may have failed or requires verification")
            return False

        except Exception as e:
            logger.error(f"LinkedIn login error: {e}")
            return False

    async def search_jobs(self, filters: dict) -> list:
        """Search LinkedIn jobs."""
        from src.core.models import Job
        jobs = []
        try:
            page = await self._get_page()

            # Build search URL
            keywords = filters.get("keywords", "")
            location = filters.get("location", "India")
            f_WT = "2" if filters.get("remote") else ""  # Remote filter
            f_AL = "true" if filters.get("easy_apply") else ""

            params = []
            if keywords:
                params.append(f"keywords={keywords}")
            if location:
                params.append(f"location={location}")
            if f_WT:
                params.append(f"f_WT={f_WT}")
            if f_AL:
                params.append(f"f_AL={f_AL}")

            url = f"{self.JOBS_URL}?{'&'.join(params)}" if params else self.JOBS_URL
            await page.goto(url, wait_until="domcontentloaded")
            await self._human_delay(3, 5)

            # Scroll to load more jobs
            for _ in range(3):
                await page.evaluate("window.scrollBy(0, 800)")
                await self._human_delay(1, 2)

            # Extract job cards
            cards = page.locator(".job-card-container, .jobs-search-results__list-item")
            count = await cards.count()

            for i in range(min(count, 25)):
                try:
                    card = cards.nth(i)
                    title_el = card.locator(".job-card-list__title, .job-card-container__link").first
                    company_el = card.locator(".job-card-container__primary-description, .artdeco-entity-lockup__subtitle").first
                    location_el = card.locator(".job-card-container__metadata-item, .artdeco-entity-lockup__caption").first

                    title = await title_el.text_content() if await title_el.count() > 0 else ""
                    company = await company_el.text_content() if await company_el.count() > 0 else ""
                    loc = await location_el.text_content() if await location_el.count() > 0 else ""

                    href = await title_el.get_attribute("href") if await title_el.count() > 0 else ""
                    if href and not href.startswith("http"):
                        href = f"{self.portal_url}{href}"

                    # Check for Easy Apply badge
                    easy_apply = card.locator(".jobs-apply-button--top-card, [aria-label*='Easy Apply']")
                    has_easy_apply = await easy_apply.count() > 0

                    if title:
                        job = Job(
                            title=title.strip(),
                            portal="linkedin",
                            url=href or "",
                            department=company.strip() if company else "",
                            location=loc.strip() if loc else "",
                            description=f"LinkedIn {'Easy Apply' if has_easy_apply else 'External'} job",
                        )
                        # Add Easy Apply flag to job metadata
                        job._easy_apply = has_easy_apply
                        jobs.append(job)

                except Exception:
                    continue

            logger.info(f"LinkedIn: Found {len(jobs)} jobs")

        except Exception as e:
            logger.error(f"LinkedIn search error: {e}")

        return jobs

    async def get_application_form(self, page, job_url: str) -> list[FormField]:
        """Get LinkedIn Easy Apply form fields."""
        fields = []
        try:
            await page.goto(job_url, wait_until="domcontentloaded")
            await self._human_delay(2, 4)

            # Click Easy Apply button
            apply_btn = page.locator("button.jobs-apply-button, button:has-text('Easy Apply')").first
            if await apply_btn.count() > 0:
                await apply_btn.click()
                await self._human_delay(2, 4)

                # Navigate through Easy Apply modal steps
                for step in range(5):  # Max 5 steps
                    modal = page.locator(".jobs-easy-apply-modal, .artdeco-modal")
                    if await modal.count() == 0:
                        break

                    # Extract fields from current step
                    inputs = modal.locator("input:not([type='hidden']), select, textarea")
                    count = await inputs.count()

                    for i in range(count):
                        try:
                            inp = inputs.nth(i)
                            name = await inp.get_attribute("name") or await inp.get_attribute("id") or f"step{step}_field{i}"
                            inp_type = await inp.get_attribute("type") or "text"

                            label_el = modal.locator(f"label[for='{name}']").first
                            label = await label_el.text_content() if await label_el.count() > 0 else ""

                            field_type = "text"
                            options = []
                            tag = await inp.evaluate("el => el.tagName.toLowerCase()")

                            if tag == "select":
                                field_type = "select"
                                options = await inp.evaluate("el => Array.from(el.options).map(o => o.text)")
                            elif inp_type == "file":
                                field_type = "file"

                            fields.append(FormField(
                                name=name,
                                field_type=field_type,
                                selector=f"[name='{name}'], #{name}",
                                label=label.strip(),
                                required=await inp.get_attribute("required") is not None,
                                options=options,
                            ))
                        except Exception:
                            continue

                    # Try next step
                    next_btn = modal.locator("button:has-text('Next'), button:has-text('Continue'), button[aria-label='Continue']").first
                    if await next_btn.count() > 0:
                        await next_btn.click()
                        await self._human_delay(1, 3)
                    else:
                        break

        except Exception as e:
            logger.error(f"LinkedIn form extraction error: {e}")

        return fields

    async def fill_application(self, page, profile_data: dict) -> bool:
        """Fill LinkedIn Easy Apply form."""
        try:
            # LinkedIn Easy Apply auto-fills from profile
            # Handle any additional fields in the modal
            modal = page.locator(".jobs-easy-apply-modal, .artdeco-modal").first
            if await modal.count() == 0:
                return True  # Nothing to fill

            # Fill visible empty fields
            inputs = modal.locator("input:not([type='hidden']):not([type='submit']), select, textarea")
            count = await inputs.count()

            for i in range(count):
                try:
                    inp = inputs.nth(i)
                    current_value = await inp.input_value()
                    if current_value:
                        continue  # Already filled

                    name = await inp.get_attribute("name") or ""
                    inp_type = await inp.get_attribute("type") or "text"

                    # Map to profile data
                    value = self._map_field(name, profile_data)
                    if value:
                        if inp_type == "select-one" or await inp.evaluate("el => el.tagName.toLowerCase()") == "select":
                            await self._select_dropdown(page, f"[name='{name}']", str(value))
                        else:
                            await self._human_type(page, f"[name='{name}']", str(value))
                        await self._human_delay(0.5, 1)

                except Exception:
                    continue

            return True

        except Exception as e:
            logger.error(f"LinkedIn form fill error: {e}")
            return False

    async def upload_documents(self, page, documents: dict) -> bool:
        """Upload resume to LinkedIn."""
        try:
            resume_path = documents.get("resume")
            if resume_path:
                upload_input = page.locator("input[type='file']").first
                if await upload_input.count() > 0:
                    await upload_input.set_input_files(resume_path)
                    await self._human_delay(2, 4)
                    logger.info(f"LinkedIn: Uploaded resume")

            return True

        except Exception as e:
            logger.error(f"LinkedIn upload error: {e}")
            return False

    async def submit_application(self, page) -> Optional[str]:
        """Submit LinkedIn Easy Apply application."""
        try:
            modal = page.locator(".jobs-easy-apply-modal, .artdeco-modal").first
            if await modal.count() == 0:
                return None

            # Navigate to final step and submit
            for _ in range(5):
                review_btn = modal.locator("button:has-text('Review'), button:has-text('Next')").first
                submit_btn = modal.locator("button:has-text('Submit application'), button:has-text('Submit')").first

                if await submit_btn.count() > 0:
                    await self._human_delay(2, 4)
                    await submit_btn.click()
                    await self._human_delay(3, 6)

                    # Check for success
                    success = page.locator(".jobs-apply-confirmation, .artdeco-inline-feedback--success")
                    if await success.count() > 0:
                        logger.info("LinkedIn: Application submitted successfully")
                        return "linkedin_easy_apply"

                    return "submitted"

                elif await review_btn.count() > 0:
                    await review_btn.click()
                    await self._human_delay(1, 3)
                else:
                    break

            return None

        except Exception as e:
            logger.error(f"LinkedIn submit error: {e}")
            return None

    def _map_field(self, field_name: str, profile_data: dict) -> Any:
        """Map LinkedIn field name to profile data."""
        name_lower = field_name.lower()
        mappings = {
            "phone": "phone",
            "mobile": "phone",
            "email": "email",
            "city": "city",
            "state": "state",
            "country": "country",
            "linkedin": "linkedin_url",
            "website": "portfolio_url",
            "salary": "expected_salary",
            "ctc": "expected_salary",
        }
        for pattern, key in mappings.items():
            if pattern in name_lower:
                return profile_data.get(key, "")
        return None
