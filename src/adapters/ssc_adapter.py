"""SSC Portal Adapter — Staff Selection Commission (ssc.nic.in)."""

from __future__ import annotations

import logging
import random
from typing import Any, Optional

from .base_adapter import BaseAdapter, FormField, ApplyResult

logger = logging.getLogger(__name__)


class SSCAdapter(BaseAdapter):
    """Adapter for SSC (ssc.nic.in) government job portal."""

    portal_name = "ssc"
    portal_url = "https://ssc.nic.in"

    LOGIN_URL = "https://ssc.nic.in/Login"
    DASHBOARD_URL = "https://ssc.nic.in/CandidateDashboard"
    APPLY_URL = "https://ssc.nic.in/OnlineApply"

    async def login(self, browser_context) -> bool:
        """Login to SSC portal."""
        try:
            page = await browser_context.new_page()
            await page.goto(self.LOGIN_URL, wait_until="domcontentloaded")
            await self._human_delay(2, 4)

            # Check if already logged in
            if "dashboard" in page.url.lower():
                logger.info("Already logged in to SSC")
                return True

            credentials = self.config.get_portal_credentials("ssc")
            if not credentials:
                logger.error("No SSC credentials configured")
                return False

            # Fill login form
            await self._human_type(page, "input[name='UserId'], #txtUserID", credentials["username"])
            await self._human_delay(0.5, 1.5)
            await self._human_type(page, "input[name='Password'], #txtPassword", credentials["password"])
            await self._human_delay(1, 2)

            # Handle text CAPTCHA (OCR-based)
            captcha_img = page.locator("img[src*='captcha'], #imgCaptcha").first
            if await captcha_img.count() > 0:
                captcha_text = await self._solve_text_captcha(page, captcha_img)
                if captcha_text:
                    await self._human_type(page, "input[name='Captcha'], #txtCaptcha", captcha_text)

            # Click login
            await self._wait_and_click(page, "input[type='submit'], #btnLogin")
            await self._human_delay(3, 5)

            if "dashboard" in page.url.lower():
                logger.info("SSC login successful")
                return True

            logger.error("SSC login failed — may need manual intervention")
            return False

        except Exception as e:
            logger.error(f"SSC login error: {e}")
            return False

    async def search_jobs(self, filters: dict) -> list:
        """Search for SSC job postings."""
        from src.core.models import Job
        jobs = []
        try:
            page = await self._get_page()
            await page.goto(f"{self.portal_url}/Portal/ActiveExams", wait_until="domcontentloaded")
            await self._human_delay(2, 4)

            # Extract active exam listings
            rows = page.locator("table.table tr, .exam-list-item")
            count = await rows.count()

            for i in range(min(count, 50)):
                try:
                    row = rows.nth(i)
                    title_el = row.locator("td:nth-child(2), .title, a").first
                    title = await title_el.text_content() if await title_el.count() > 0 else ""
                    link = await title_el.get_attribute("href") if await title_el.count() > 0 else ""

                    if title and len(title.strip()) > 5:
                        # Extract deadline
                        date_el = row.locator("td:nth-child(4), .deadline").first
                        deadline = await date_el.text_content() if await date_el.count() > 0 else ""

                        job = Job(
                            title=title.strip(),
                            portal="ssc",
                            url=link or f"{self.portal_url}/OnlineApply",
                            department="SSC",
                            last_date=self._parse_date_str(deadline),
                            description=f"SSC Examination: {title.strip()}",
                        )
                        jobs.append(job)
                except Exception:
                    continue

            logger.info(f"SSC: Found {len(jobs)} active exams")

        except Exception as e:
            logger.error(f"SSC search error: {e}")

        return jobs

    async def get_application_form(self, page, job_url: str) -> list[FormField]:
        """Get SSC application form fields."""
        fields = []
        try:
            await page.goto(job_url, wait_until="domcontentloaded")
            await self._human_delay(2, 4)

            # SSC uses standard form fields
            form_inputs = page.locator("input[type='text'], input[type='email'], input[type='tel'], "
                                        "input[type='date'], select, textarea, input[type='file']")
            count = await form_inputs.count()

            for i in range(count):
                try:
                    inp = form_inputs.nth(i)
                    name = await inp.get_attribute("name") or await inp.get_attribute("id") or f"field_{i}"
                    tag = await inp.evaluate("el => el.tagName.toLowerCase()")
                    inp_type = await inp.get_attribute("type") or "text"

                    # Get label
                    label_el = page.locator(f"label[for='{name}'], label:has(input[name='{name}'])").first
                    label = await label_el.text_content() if await label_el.count() > 0 else ""

                    # Determine field type
                    if tag == "select":
                        field_type = "select"
                        options = await inp.evaluate("el => Array.from(el.options).map(o => o.text)")
                    elif inp_type == "file":
                        field_type = "file"
                        options = []
                    elif inp_type == "date":
                        field_type = "date"
                        options = []
                    else:
                        field_type = "text"
                        options = []

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
            logger.error(f"SSC form extraction error: {e}")

        return fields

    async def fill_application(self, page, profile_data: dict) -> bool:
        """Fill SSC application form."""
        try:
            # Personal details
            field_mappings = {
                "txtName": "full_name",
                "txtFatherName": "father_name",
                "txtDOB": "dob",
                "ddlGender": "gender",
                "ddlCategory": "category",
                "txtEmail": "email",
                "txtMobile": "phone",
                "txtAddress": "address_line1",
                "txtCity": "city",
                "ddlState": "state",
                "txtPin": "pincode",
            }

            for selector, key in field_mappings.items():
                value = self._get_nested(profile_data, key)
                if value:
                    el = page.locator(f"#{selector}, [name='{selector}']").first
                    if await el.count() > 0:
                        tag = await el.evaluate("el => el.tagName.toLowerCase()")
                        if tag == "select":
                            await self._select_dropdown(page, f"#{selector}", str(value))
                        else:
                            await self._human_type(page, f"#{selector}", str(value))
                        await self._human_delay(0.5, 1.5)

            # Education details
            education = profile_data.get("education", [])
            for i, edu in enumerate(education[:3]):  # SSC typically asks for 3 entries
                prefix = f"Education_{i}_"
                await self._fill_education_block(page, prefix, edu)

            logger.info("SSC form filled successfully")
            return True

        except Exception as e:
            logger.error(f"SSC form fill error: {e}")
            return False

    async def upload_documents(self, page, documents: dict) -> bool:
        """Upload documents to SSC form."""
        try:
            upload_map = {
                "photo": ("input[type='file'][name*='Photo'], #fuPhoto", 20, 50),  # 20-50KB
                "signature": ("input[type='file'][name*='Sign'], #fuSign", 10, 20),  # 10-20KB
                "certificate": ("input[type='file'][name*='Cert'], #fuCert", 50, 500),
            }

            for doc_key, (selector, min_kb, max_kb) in upload_map.items():
                file_path = documents.get(doc_key)
                if file_path:
                    el = page.locator(selector).first
                    if await el.count() > 0:
                        await el.set_input_files(file_path)
                        await self._human_delay(1, 2)
                        logger.info(f"Uploaded {doc_key}: {file_path}")

            return True

        except Exception as e:
            logger.error(f"SSC document upload error: {e}")
            return False

    async def submit_application(self, page) -> Optional[str]:
        """Submit SSC application."""
        try:
            # Look for submit button
            submit_btn = page.locator("input[type='submit'][value*='Submit'], #btnSubmit").first
            if await submit_btn.count() > 0:
                await self._human_delay(2, 4)
                await submit_btn.click()
                await self._human_delay(3, 6)

                # Extract reference ID
                ref_el = page.locator("#lblRefNo, .reference-number, td:has-text('Reference')").first
                if await ref_el.count() > 0:
                    ref_text = await ref_el.text_content()
                    # Extract numeric reference
                    import re
                    match = re.search(r'\d{10,}', ref_text)
                    if match:
                        return match.group(0)

                logger.info("SSC application submitted")
                return "submitted"

            return None

        except Exception as e:
            logger.error(f"SSC submit error: {e}")
            return None

    async def _solve_text_captcha(self, page, captcha_element) -> str:
        """Solve text-based CAPTCHA using OCR."""
        try:
            # Screenshot the captcha
            await captcha_element.screenshot(path="/tmp/ssc_captcha.png")

            # Try Tesseract OCR
            import subprocess
            result = subprocess.run(
                ["tesseract", "/tmp/ssc_captcha.png", "stdout", "--psm", "7", "-c", "tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                text = result.stdout.strip().replace(" ", "")
                if 4 <= len(text) <= 8:
                    return text

            return ""
        except Exception:
            return ""

    async def _fill_education_block(self, page, prefix: str, edu: dict):
        """Fill education section."""
        mappings = {
            f"{prefix}Degree": edu.get("degree", ""),
            f"{prefix}University": edu.get("university", ""),
            f"{prefix}Year": str(edu.get("year_of_passing", "")),
            f"{prefix}Percentage": str(edu.get("percentage", "")),
        }
        for selector, value in mappings.items():
            if value:
                el = page.locator(f"#{selector}, [name='{selector}']").first
                if await el.count() > 0:
                    await self._human_type(page, f"#{selector}", value)
                    await self._human_delay(0.3, 0.8)

    def _get_nested(self, data: dict, key: str) -> Any:
        """Get value from flat or nested dict."""
        if key in data:
            return data[key]
        for section in ("personal", "contact", "address"):
            if section in data and isinstance(data[section], dict) and key in data[section]:
                return data[section][key]
        return None

    def _parse_date_str(self, text: str):
        """Parse date from various formats."""
        import re
        from datetime import datetime
        patterns = [
            (r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', "%d/%m/%Y"),
            (r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})', "%Y/%m/%d"),
        ]
        for pattern, fmt in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return datetime.strptime(match.group(0).replace("-", "/"), fmt).date()
                except ValueError:
                    continue
        return None
