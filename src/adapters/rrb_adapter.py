"""RRB (Railway Recruitment Board) Adapter."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Optional

from .base_adapter import BaseAdapter, FormField, ApplyResult

logger = logging.getLogger(__name__)


class RRBAdapter(BaseAdapter):
    """Adapter for RRB (Indian Railways) recruitment portal."""

    portal_name = "rrb"
    portal_url = "https://www.rrbcdg.gov.in"

    async def login(self, browser_context) -> bool:
        try:
            page = await browser_context.new_page()
            await page.goto(f"{self.portal_url}/CandidateLogin", wait_until="domcontentloaded")
            await self._human_delay(2, 4)

            credentials = self.config.get_portal_credentials("rrb")
            if not credentials:
                logger.error("No RRB credentials configured")
                return False

            reg_no = credentials.get("registration_no", credentials["username"])
            await self._human_type(page, "#txtRegNo, input[name='RegistrationNo']", reg_no)
            await self._human_delay(0.5, 1)
            await self._human_type(page, "#txtDOB, input[name='DOB']", credentials.get("dob", ""))
            await self._human_delay(0.5, 1)

            # Captcha
            captcha_el = page.locator("img[src*='captcha']").first
            if await captcha_el.count() > 0:
                captcha = await self._solve_text_captcha(page, captcha_el)
                if captcha:
                    await self._human_type(page, "#txtCaptcha, input[name='Captcha']", captcha)

            await self._wait_and_click(page, "#btnLogin, input[type='submit']")
            await self._human_delay(3, 5)

            logger.info("RRB login attempted")
            return True

        except Exception as e:
            logger.error(f"RRB login error: {e}")
            return False

    async def search_jobs(self, filters: dict) -> list:
        from src.core.models import Job
        jobs = []
        try:
            page = await self._get_page()
            await page.goto(f"{self.portal_url}/Notifications", wait_until="domcontentloaded")
            await self._human_delay(2, 4)

            items = page.locator("table tr, .notification-item")
            count = await items.count()

            for i in range(min(count, 20)):
                try:
                    item = items.nth(i)
                    title_el = item.locator("a, td:nth-child(2)").first
                    if await title_el.count() == 0:
                        continue

                    title = await title_el.text_content()
                    href = await title_el.get_attribute("href") or ""

                    if title and "recruitment" in title.lower() or "ntpc" in title.lower() or "group" in title.lower():
                        jobs.append(Job(
                            title=title.strip(),
                            portal="rrb",
                            url=href if href.startswith("http") else f"{self.portal_url}{href}",
                            department="Indian Railways",
                            description=f"RRB Recruitment: {title.strip()}",
                        ))

                except Exception:
                    continue

            logger.info(f"RRB: Found {len(jobs)} notifications")

        except Exception as e:
            logger.error(f"RRB search error: {e}")

        return jobs

    async def get_application_form(self, page, job_url: str) -> list[FormField]:
        fields = []
        try:
            await page.goto(job_url, wait_until="domcontentloaded")
            await self._human_delay(2, 4)

            form_inputs = page.locator("input:not([type='hidden']), select, textarea")
            count = await form_inputs.count()

            for i in range(min(count, 40)):
                try:
                    inp = form_inputs.nth(i)
                    name = await inp.get_attribute("name") or f"field_{i}"
                    inp_type = await inp.get_attribute("type") or "text"
                    tag = await inp.evaluate("el => el.tagName.toLowerCase()")

                    field_type = "text"
                    options = []
                    if tag == "select":
                        field_type = "select"
                        options = await inp.evaluate("el => Array.from(el.options).map(o => o.text)")
                    elif inp_type == "file":
                        field_type = "file"
                    elif inp_type == "radio":
                        field_type = "radio"

                    fields.append(FormField(
                        name=name,
                        field_type=field_type,
                        selector=f"[name='{name}']",
                        options=options,
                    ))
                except Exception:
                    continue

        except Exception as e:
            logger.error(f"RRB form extraction error: {e}")

        return fields

    async def fill_application(self, page, profile_data: dict) -> bool:
        try:
            field_map = {
                "RegistrationNo": "registration_no",
                "Name": "full_name",
                "FatherName": "father_name",
                "DOB": "dob",
                "Gender": "gender",
                "Category": "category",
                "Email": "email",
                "Mobile": "phone",
                "Address": "address_line1",
                "State": "state",
                "Pincode": "pincode",
            }
            for selector, key in field_map.items():
                value = self._get_nested(profile_data, key)
                if value:
                    el = page.locator(f"[name='{selector}'], #{selector}").first
                    if await el.count() > 0:
                        await self._human_type(page, f"[name='{selector}'], #{selector}", str(value))
                        await self._human_delay(0.3, 0.8)

            logger.info("RRB form filled")
            return True
        except Exception as e:
            logger.error(f"RRB form fill error: {e}")
            return False

    async def upload_documents(self, page, documents: dict) -> bool:
        try:
            for key in ("photo", "signature", "certificate"):
                path = documents.get(key)
                if path:
                    el = page.locator(f"input[type='file'][name*='{key.title()}', #{'fu'+key.title()}]").first
                    if await el.count() > 0:
                        await el.set_input_files(path)
                        await self._human_delay(1, 2)
            return True
        except Exception:
            return False

    async def submit_application(self, page) -> Optional[str]:
        try:
            btn = page.locator("#btnSubmit, input[value*='Submit']").first
            if await btn.count() > 0:
                await self._human_delay(2, 4)
                await btn.click()
                await self._human_delay(3, 6)
                ref = page.locator("#lblRefNo, .reference-number").first
                if await ref.count() > 0:
                    text = await ref.text_content()
                    match = re.search(r'\d{10,}', text)
                    if match:
                        return match.group(0)
                return "submitted"
            return None
        except Exception as e:
            logger.error(f"RRB submit error: {e}")
            return None

    async def _solve_text_captcha(self, page, captcha_element) -> str:
        try:
            await captcha_element.screenshot(path="/tmp/rrb_captcha.png")
            import subprocess
            result = subprocess.run(
                ["tesseract", "/tmp/rrb_captcha.png", "stdout", "--psm", "7"],
                capture_output=True, text=True, timeout=10,
            )
            return result.stdout.strip().replace(" ", "") if result.returncode == 0 else ""
        except Exception:
            return ""

    def _get_nested(self, data: dict, key: str) -> Any:
        if key in data:
            return data[key]
        for section in ("personal", "contact", "address"):
            if section in data and isinstance(data[section], dict) and key in data[section]:
                return data[section][key]
        return None
