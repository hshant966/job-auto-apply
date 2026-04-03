"""IBPS (Institute of Banking Personnel Selection) Adapter."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Optional

from .base_adapter import BaseAdapter, FormField, ApplyResult

logger = logging.getLogger(__name__)


class IBPSAdapter(BaseAdapter):
    """Adapter for IBPS (ibps.in) — Clerk, PO, SO recruitment."""

    portal_name = "ibps"
    portal_url = "https://www.ibps.in"

    async def login(self, browser_context) -> bool:
        try:
            page = await browser_context.new_page()
            await page.goto(f"{self.portal_url}", wait_until="domcontentloaded")
            await self._human_delay(2, 4)

            credentials = self.config.get_portal_credentials("ibps")
            if not credentials:
                logger.error("No IBPS credentials configured")
                return False

            # IBPS uses CRP registration
            login_el = page.locator("a:has-text('Login'), a:has-text('CRP')").first
            if await login_el.count() > 0:
                await login_el.click()
                await self._human_delay(2, 4)

            await self._human_type(page, "input[name='userId'], #userId", credentials["username"])
            await self._human_delay(0.5, 1)
            await self._human_type(page, "input[name='password'], #password", credentials["password"])
            await self._human_delay(0.5, 1)

            # reCAPTCHA
            recaptcha = page.locator(".g-recaptcha, iframe[src*='recaptcha']").first
            if await recaptcha.count() > 0:
                logger.warning("IBPS: reCAPTCHA detected — may need manual solve")

            await self._wait_and_click(page, "input[type='submit'], #btnLogin")
            await self._human_delay(3, 5)

            logger.info("IBPS login attempted")
            return True

        except Exception as e:
            logger.error(f"IBPS login error: {e}")
            return False

    async def search_jobs(self, filters: dict) -> list:
        from src.core.models import Job
        jobs = []
        try:
            page = await self._get_page()
            await page.goto(f"{self.portal_url}/crp-clerks-xiv/", wait_until="domcontentloaded")
            await self._human_delay(2, 4)

            # Look for notification/advertisement links
            links = page.locator("a[href*='notification'], a[href*='advertisement'], a[href*='notification']")
            count = await links.count()

            for i in range(min(count, 10)):
                try:
                    link = links.nth(i)
                    text = await link.text_content()
                    href = await link.get_attribute("href") or ""

                    if text and len(text.strip()) > 5:
                        jobs.append(Job(
                            title=text.strip(),
                            portal="ibps",
                            url=href if href.startswith("http") else f"{self.portal_url}{href}",
                            department="Banking",
                            description=f"IBPS: {text.strip()}",
                        ))
                except Exception:
                    continue

            # Also check main page for current CRPs
            current_crps = page.locator(".crp-list, .current-recruitment, .notification-list")
            if await current_crps.count() > 0:
                crp_links = current_crps.first.locator("a")
                crp_count = await crp_links.count()
                for i in range(min(crp_count, 5)):
                    try:
                        link = crp_links.nth(i)
                        text = await link.text_content()
                        href = await link.get_attribute("href") or ""
                        if text:
                            jobs.append(Job(
                                title=text.strip(),
                                portal="ibps",
                                url=href if href.startswith("http") else f"{self.portal_url}{href}",
                                department="Banking",
                            ))
                    except Exception:
                        continue

            logger.info(f"IBPS: Found {len(jobs)} notifications")

        except Exception as e:
            logger.error(f"IBPS search error: {e}")

        return jobs

    async def get_application_form(self, page, job_url: str) -> list[FormField]:
        fields = []
        try:
            await page.goto(job_url, wait_until="domcontentloaded")
            await self._human_delay(2, 4)

            form_inputs = page.locator("input:not([type='hidden']), select, textarea")
            count = await form_inputs.count()

            for i in range(min(count, 50)):
                try:
                    inp = form_inputs.nth(i)
                    name = await inp.get_attribute("name") or f"field_{i}"
                    inp_type = await inp.get_attribute("type") or "text"
                    tag = await inp.evaluate("el => el.tagName.toLowerCase()")

                    if inp_type in ("hidden", "button", "submit"):
                        continue

                    field_type = "text"
                    options = []
                    if tag == "select":
                        field_type = "select"
                        options = await inp.evaluate("el => Array.from(el.options).map(o => o.text)")
                    elif inp_type == "file":
                        field_type = "file"
                    elif inp_type == "radio":
                        field_type = "radio"
                    elif inp_type == "checkbox":
                        field_type = "checkbox"

                    fields.append(FormField(
                        name=name,
                        field_type=field_type,
                        selector=f"[name='{name}'], #{name}",
                        options=options,
                    ))
                except Exception:
                    continue

        except Exception as e:
            logger.error(f"IBPS form extraction error: {e}")

        return fields

    async def fill_application(self, page, profile_data: dict) -> bool:
        try:
            field_map = {
                "candidateName": "full_name",
                "fatherName": "father_name",
                "dob": "dob",
                "gender": "gender",
                "category": "category",
                "email": "email",
                "mobile": "phone",
                "address": "address_line1",
                "state": "state",
                "pincode": "pincode",
                "qualification": "degree",
            }
            for selector, key in field_map.items():
                value = self._get_nested(profile_data, key)
                if value:
                    el = page.locator(f"#{selector}, [name='{selector}']").first
                    if await el.count() > 0:
                        tag = await el.evaluate("el => el.tagName.toLowerCase()")
                        if tag == "select":
                            await self._select_dropdown(page, f"#{selector}", str(value))
                        else:
                            await self._human_type(page, f"#{selector}", str(value))
                        await self._human_delay(0.3, 0.8)

            # Bank preferences (IBPS-specific)
            prefs = profile_data.get("bank_preferences", [])
            for i, bank in enumerate(prefs[:5]):
                pref_el = page.locator(f"#preference{i+1}, [name='Preference{i+1}']").first
                if await pref_el.count() > 0:
                    await self._select_dropdown(page, f"#preference{i+1}", bank)
                    await self._human_delay(0.3, 0.5)

            logger.info("IBPS form filled")
            return True
        except Exception as e:
            logger.error(f"IBPS form fill error: {e}")
            return False

    async def upload_documents(self, page, documents: dict) -> bool:
        try:
            uploads = {
                "photo": ("Photo", 20, 50),
                "signature": ("Sign", 10, 20),
                "thumb": ("Thumb", 10, 50),
            }
            for doc_key, (label, _, _) in uploads.items():
                path = documents.get(doc_key)
                if path:
                    el = page.locator(f"input[type='file'][name*='{label}']").first
                    if await el.count() > 0:
                        await el.set_input_files(path)
                        await self._human_delay(1, 2)
            return True
        except Exception:
            return False

    async def submit_application(self, page) -> Optional[str]:
        try:
            btn = page.locator("#btnSubmit, input[value*='Submit'], button:has-text('Submit')").first
            if await btn.count() > 0:
                await self._human_delay(2, 4)
                await btn.click()
                await self._human_delay(3, 6)
                ref = page.locator("#lblRefNo, .application-number").first
                if await ref.count() > 0:
                    text = await ref.text_content()
                    match = re.search(r'\d{10,}', text)
                    if match:
                        return match.group(0)
                return "submitted"
            return None
        except Exception as e:
            logger.error(f"IBPS submit error: {e}")
            return None

    def _get_nested(self, data: dict, key: str) -> Any:
        if key in data:
            return data[key]
        for section in ("personal", "contact", "address"):
            if section in data and isinstance(data[section], dict) and key in data[section]:
                return data[section][key]
        return None
