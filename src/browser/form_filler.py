"""Form filler — intelligent form detection and filling."""

from __future__ import annotations

import logging
import random
from typing import Optional

from .stealth import StealthManager

logger = logging.getLogger(__name__)

FIELD_SELECTORS = {
    "name": ['input[name*="name"]', '#name', '#fullName', 'input[placeholder*="name" i]'],
    "email": ['input[name*="email"]', '#email', 'input[type="email"]'],
    "phone": ['input[name*="phone"]', 'input[name*="mobile"]', '#phone', '#mobile', 'input[type="tel"]'],
    "dob": ['input[name*="dob"]', 'input[name*="birth"]', '#dateOfBirth', '#dob'],
    "address": ['textarea[name*="address"]', '#address', 'input[name*="address"]'],
    "city": ['input[name*="city"]', '#city'],
    "state": ['select[name*="state"]', '#state'],
    "pincode": ['input[name*="pin"]', '#pincode', '#zip'],
    "gender": ['select[name*="gender"]', '#gender'],
    "category": ['select[name*="category"]', '#category'],
    "father": ['input[name*="father"]', '#fatherName'],
    "qualification": ['select[name*="qualification"]', '#qualification'],
}


class FormFiller:
    """Detect and fill web forms with profile data."""

    def __init__(self):
        self._stealth = StealthManager()

    async def detect_fields(self, page) -> list[dict]:
        """Detect form fields on the current page."""
        fields = []
        try:
            inputs = await page.query_selector_all("input, select, textarea")
            for inp in inputs:
                name = await inp.get_attribute("name") or ""
                input_type = await inp.get_attribute("type") or "text"
                placeholder = await inp.get_attribute("placeholder") or ""
                label_text = ""
                inp_id = await inp.get_attribute("id") or ""
                if inp_id:
                    label_el = await page.query_selector(f'label[for="{inp_id}"]')
                    if label_el:
                        label_text = await label_el.inner_text()
                fields.append({
                    "name": name,
                    "type": input_type,
                    "id": inp_id,
                    "placeholder": placeholder,
                    "label": label_text,
                    "selector": f'#{inp_id}' if inp_id else f'[name="{name}"]' if name else "",
                })
        except Exception as e:
            logger.warning(f"Field detection error: {e}")
        return fields

    async def fill_form(self, page, profile_data: dict) -> dict:
        """Fill detected form fields with profile data."""
        filled = {}
        mapping = {
            "name": profile_data.get("full_name", ""),
            "email": profile_data.get("email", ""),
            "phone": profile_data.get("phone", ""),
            "dob": profile_data.get("dob", ""),
            "address": profile_data.get("address_line1", "") + " " + profile_data.get("address_line2", ""),
            "city": profile_data.get("city", ""),
            "pincode": profile_data.get("pincode", ""),
            "father": profile_data.get("father_name", ""),
        }

        for field_key, selectors in FIELD_SELECTORS.items():
            value = mapping.get(field_key, "")
            if not value:
                continue
            for sel in selectors:
                try:
                    el = await page.query_selector(sel)
                    if el:
                        await el.click()
                        await el.fill("")
                        await StealthManager.human_type(page, sel, str(value).strip())
                        filled[field_key] = value
                        await StealthManager.human_delay(300, 800)
                        break
                except Exception:
                    continue

        # Handle select dropdowns
        for sel_key in ["gender", "category", "state", "qualification"]:
            value = profile_data.get(sel_key, "")
            if not value:
                continue
            for sel in FIELD_SELECTORS.get(sel_key, []):
                try:
                    el = await page.query_selector(sel)
                    if el:
                        tag = await el.evaluate("e => e.tagName")
                        if tag == "SELECT":
                            await page.select_option(sel, label=value)
                            filled[sel_key] = value
                            break
                except Exception:
                    try:
                        await page.select_option(sel, value=value)
                        filled[sel_key] = value
                        break
                    except Exception:
                        continue

        logger.info(f"Filled {len(filled)} fields")
        return filled

    async def upload_documents(self, page, documents: dict) -> dict:
        """Upload files to form inputs."""
        uploaded = {}
        file_selectors = {
            "photo": ['input[type="file"][accept*="image"]', '#photoUpload', 'input[name*="photo"]'],
            "signature": ['input[type="file"][name*="signature"]', '#signatureUpload'],
            "resume": ['input[type="file"][name*="resume"]', '#resumeUpload', 'input[type="file"][accept*="pdf"]'],
            "certificate": ['input[type="file"][name*="certificate"]', '#certificateUpload'],
        }

        for doc_type, file_path in documents.items():
            if not file_path:
                continue
            selectors = file_selectors.get(doc_type, [f'input[type="file"][name*="{doc_type}"]'])
            for sel in selectors:
                try:
                    el = await page.query_selector(sel)
                    if el:
                        await el.set_input_files(file_path)
                        uploaded[doc_type] = file_path
                        await StealthManager.human_delay(1000, 2000)
                        break
                except Exception:
                    continue

        logger.info(f"Uploaded {len(uploaded)} documents")
        return uploaded
