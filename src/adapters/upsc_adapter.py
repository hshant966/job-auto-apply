"""UPSC Portal Adapter — Union Public Service Commission (upsc.gov.in)."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Optional

from .base_adapter import BaseAdapter, FormField, ApplyResult

logger = logging.getLogger(__name__)


class UPSCAdapter(BaseAdapter):
    """Adapter for UPSC (upsc.gov.in) — uses OTR (One Time Registration)."""

    portal_name = "upsc"
    portal_url = "https://upsc.gov.in"

    OTR_URL = "https://otr.pariksha.nic.in"
    LOGIN_URL = "https://otr.pariksha.nic.in/Login"
    CAF_URL = "https://otr.pariksha.nic.in/CommonApplicationForm"

    async def login(self, browser_context) -> bool:
        """Login to UPSC OTR portal."""
        try:
            page = await browser_context.new_page()
            await page.goto(self.LOGIN_URL, wait_until="domcontentloaded")
            await self._human_delay(2, 4)

            credentials = self.config.get_portal_credentials("upsc")
            if not credentials:
                logger.error("No UPSC credentials configured")
                return False

            # 2026: New OTR system
            await self._human_type(page, "#txtEmail, input[name='email']", credentials["username"])
            await self._human_delay(0.5, 1)
            await self._human_type(page, "#txtPassword, input[name='password']", credentials["password"])
            await self._human_delay(1, 2)

            # Handle CAPTCHA
            captcha_el = page.locator("img[src*='captcha']").first
            if await captcha_el.count() > 0:
                captcha = await self._solve_text_captcha(page, captcha_el)
                if captcha:
                    await self._human_type(page, "#txtCaptcha, input[name='captcha']", captcha)

            await self._wait_and_click(page, "#btnLogin, input[type='submit']")
            await self._human_delay(3, 5)

            # Verify login success
            if "dashboard" in page.url.lower() or "otr" in page.url.lower():
                logger.info("UPSC login successful")
                return True

            return False

        except Exception as e:
            logger.error(f"UPSC login error: {e}")
            return False

    async def search_jobs(self, filters: dict) -> list:
        """Search for UPSC exam notifications."""
        from src.core.models import Job
        jobs = []
        try:
            page = await self._get_page()
            await page.goto(f"{self.portal_url}/examinations", wait_until="domcontentloaded")
            await self._human_delay(2, 4)

            # Parse exam notifications
            items = page.locator(".view-content .views-row, .notification-item, tr")
            count = await items.count()

            for i in range(min(count, 30)):
                try:
                    item = items.nth(i)
                    title_el = item.locator("a, .title, td:nth-child(1)").first
                    if await title_el.count() == 0:
                        continue

                    title = await title_el.text_content()
                    href = await title_el.get_attribute("href") or ""

                    if not title or len(title.strip()) < 5:
                        continue

                    # Extract dates
                    date_el = item.locator("td:nth-child(3), .date, .deadline").first
                    deadline = ""
                    if await date_el.count() > 0:
                        deadline = await date_el.text_content() or ""

                    job = Job(
                        title=title.strip(),
                        portal="upsc",
                        url=href if href.startswith("http") else f"{self.portal_url}{href}",
                        department="UPSC",
                        last_date=self._parse_date_str(deadline),
                        description=f"UPSC Examination: {title.strip()}",
                    )
                    jobs.append(job)

                except Exception:
                    continue

            logger.info(f"UPSC: Found {len(jobs)} examinations")

        except Exception as e:
            logger.error(f"UPSC search error: {e}")

        return jobs

    async def get_application_form(self, page, job_url: str) -> list[FormField]:
        """Get UPSC CAF (Common Application Form) fields."""
        fields = []
        try:
            await page.goto(job_url, wait_until="domcontentloaded")
            await self._human_delay(2, 4)

            # 2026: Live Photo Capture section
            fields.append(FormField(
                name="live_photo",
                field_type="photo_capture",
                selector="#btnCapture, .photo-capture",
                label="Live Photo (2026 requirement)",
                required=True,
            ))

            # Standard form fields
            form_inputs = page.locator("input:not([type='hidden']), select, textarea")
            count = await form_inputs.count()

            for i in range(min(count, 50)):
                try:
                    inp = form_inputs.nth(i)
                    name = await inp.get_attribute("name") or await inp.get_attribute("id") or f"field_{i}"
                    inp_type = await inp.get_attribute("type") or "text"

                    if inp_type in ("hidden", "button", "submit", "image"):
                        continue

                    label_el = page.locator(f"label[for='{name}']").first
                    label = await label_el.text_content() if await label_el.count() > 0 else ""

                    field_type = "text"
                    options = []
                    tag = await inp.evaluate("el => el.tagName.toLowerCase()")

                    if tag == "select":
                        field_type = "select"
                        options = await inp.evaluate("el => Array.from(el.options).map(o => o.text)")
                    elif inp_type == "file":
                        field_type = "file"
                    elif inp_type == "date":
                        field_type = "date"
                    elif inp_type == "radio":
                        field_type = "radio"
                    elif inp_type == "checkbox":
                        field_type = "checkbox"

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

        except Exception as e:
            logger.error(f"UPSC form extraction error: {e}")

        return fields

    async def fill_application(self, page, profile_data: dict) -> bool:
        """Fill UPSC CAF form — mostly auto-prefilled from OTR."""
        try:
            # UPSC CAF auto-fills from OTR, but may need:
            # 1. Exam-specific preferences
            # 2. Center selection
            # 3. Optional subject selection

            center_field = page.locator("#ddlCenter, [name*='Center']").first
            if await center_field.count() > 0:
                preferred_centers = profile_data.get("preferred_centers", ["Delhi"])
                if preferred_centers:
                    await self._select_dropdown(page, "#ddlCenter, [name*='Center']", preferred_centers[0])
                    await self._human_delay(0.5, 1)

            # Optional subject (for CSE)
            opt_field = page.locator("#ddlOptional, [name*='Optional']").first
            if await opt_field.count() > 0:
                optional = profile_data.get("optional_subject", "")
                if optional:
                    await self._select_dropdown(page, "#ddlOptional, [name*='Optional']", optional)
                    await self._human_delay(0.5, 1)

            # Medium of examination
            medium_field = page.locator("#ddlMedium, [name*='Medium']").first
            if await medium_field.count() > 0:
                await self._select_dropdown(page, "#ddlMedium, [name*='Medium']", "English")
                await self._human_delay(0.5, 1)

            logger.info("UPSC application preferences filled")
            return True

        except Exception as e:
            logger.error(f"UPSC form fill error: {e}")
            return False

    async def upload_documents(self, page, documents: dict) -> bool:
        """Upload documents — UPSC 2026 uses live photo capture."""
        try:
            # Live photo capture (2026 requirement)
            capture_btn = page.locator("#btnCapture, .photo-capture-btn").first
            if await capture_btn.count() > 0:
                # For automation: use pre-captured photo
                photo_path = documents.get("photo")
                if photo_path:
                    photo_input = page.locator("input[type='file'][name*='Photo']").first
                    if await photo_input.count() > 0:
                        await photo_input.set_input_files(photo_path)
                        await self._human_delay(1, 2)

            # Signature upload
            sig_input = page.locator("input[type='file'][name*='Sign']").first
            if await sig_input.count() > 0:
                sig_path = documents.get("signature")
                if sig_path:
                    await sig_input.set_input_files(sig_path)
                    await self._human_delay(1, 2)

            # Category certificate (if applicable)
            cert_input = page.locator("input[type='file'][name*='Cert']").first
            if await cert_input.count() > 0:
                cert_path = documents.get("caste_certificate") or documents.get("ews_certificate")
                if cert_path:
                    await cert_input.set_input_files(cert_path)
                    await self._human_delay(1, 2)

            return True

        except Exception as e:
            logger.error(f"UPSC document upload error: {e}")
            return False

    async def submit_application(self, page) -> Optional[str]:
        """Submit UPSC application."""
        try:
            submit_btn = page.locator("#btnSubmit, input[value*='Submit']").first
            if await submit_btn.count() > 0:
                await self._human_delay(2, 4)
                await submit_btn.click()
                await self._human_delay(3, 6)

                # Extract reference/application number
                ref_el = page.locator("#lblAppNo, .application-number, td:has-text('Application')").first
                if await ref_el.count() > 0:
                    ref_text = await ref_el.text_content()
                    match = re.search(r'\d{10,}', ref_text)
                    if match:
                        return match.group(0)

                return "submitted"

            return None

        except Exception as e:
            logger.error(f"UPSC submit error: {e}")
            return None

    async def _solve_text_captcha(self, page, captcha_element) -> str:
        try:
            await captcha_element.screenshot(path="/tmp/upsc_captcha.png")
            import subprocess
            result = subprocess.run(
                ["tesseract", "/tmp/upsc_captcha.png", "stdout", "--psm", "7"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip().replace(" ", "")
            return ""
        except Exception:
            return ""

    def _parse_date_str(self, text: str):
        if not text:
            return None
        match = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', text)
        if match:
            try:
                return datetime.strptime(match.group(0).replace("-", "/"), "%d/%m/%Y").date()
            except ValueError:
                pass
        return None
