"""Base Adapter — abstract interface for portal adapters."""

from __future__ import annotations

import asyncio
import logging
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from src.core.models import Job

logger = logging.getLogger(__name__)


class AdapterState(Enum):
    IDLE = "idle"
    LOGGED_IN = "logged_in"
    SEARCHING = "searching"
    APPLYING = "applying"
    ERROR = "error"


@dataclass
class FormField:
    name: str
    field_type: str
    selector: str
    label: str = ""
    required: bool = False
    options: list[str] = field(default_factory=list)


@dataclass
class ApplyResult:
    success: bool
    reference_id: Optional[str] = None
    error: Optional[str] = None
    screenshot_path: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


class BaseAdapter(ABC):
    portal_name: str = ""
    portal_url: str = ""
    state: AdapterState = AdapterState.IDLE

    def __init__(self, config=None):
        self.config = config
        self.state = AdapterState.IDLE

    @abstractmethod
    async def login(self, browser_context) -> bool:
        ...

    @abstractmethod
    async def search_jobs(self, filters: dict) -> list[Job]:
        ...

    @abstractmethod
    async def get_application_form(self, page, job_url: str) -> list[FormField]:
        ...

    @abstractmethod
    async def fill_application(self, page, profile_data: dict) -> bool:
        ...

    @abstractmethod
    async def upload_documents(self, page, documents: dict) -> bool:
        ...

    @abstractmethod
    async def submit_application(self, page) -> Optional[str]:
        ...

    async def check_status(self, page, reference_id: str) -> str:
        return "unknown"

    async def _human_delay(self, min_s: float = 1.0, max_s: float = 3.0):
        await asyncio.sleep(random.uniform(min_s, max_s))

    async def _human_type(self, page, selector: str, text: str):
        try:
            await page.click(selector)
            await page.fill(selector, "")
            for ch in text:
                await page.type(selector, ch, delay=random.randint(50, 150))
                if random.random() < 0.1:
                    await asyncio.sleep(random.uniform(0.1, 0.3))
        except Exception:
            try:
                await page.fill(selector, text)
            except Exception:
                pass

    async def _screenshot(self, page, name: str) -> str:
        path = f"data/screenshots/{self.portal_name}_{name}_{int(datetime.now().timestamp())}.png"
        await page.screenshot(path=path)
        return path

    async def _wait_click(self, page, selector: str, timeout: int = 10000) -> bool:
        try:
            await page.wait_for_selector(selector, timeout=timeout)
            await page.click(selector)
            return True
        except Exception:
            return False

    async def _select_option(self, page, selector: str, value: str) -> bool:
        try:
            await page.select_option(selector, label=value)
            return True
        except Exception:
            try:
                await page.select_option(selector, value=value)
                return True
            except Exception:
                return False

    async def _upload_file(self, page, selector: str, file_path: str) -> bool:
        try:
            await page.set_input_files(selector, file_path)
            return True
        except Exception:
            return False
