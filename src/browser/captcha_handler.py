"""CAPTCHA detection and solving — multi-strategy with OCR, AI, paid services, and manual fallback."""

from __future__ import annotations

import asyncio
import hashlib
import io
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

class CaptchaType(str, Enum):
    TEXT_IMAGE = "text_image"          # Simple text in an image
    RECAPTCHA_V2 = "recaptcha_v2"     # Google reCAPTCHA v2 checkbox
    RECAPTCHA_V3 = "recaptcha_v3"     # Google reCAPTCHA v3 (invisible)
    HCAPTCHA = "hcaptcha"             # hCaptcha
    SLIDER = "slider"                 # Slider / drag puzzle
    IMAGE_SELECT = "image_select"     # "Select all traffic lights"
    MATH = "math"                     # Simple math equation
    UNKNOWN = "unknown"


class SolveStrategy(str, Enum):
    OCR = "ocr"
    AI = "ai"
    PAID_SERVICE = "paid_service"
    MANUAL = "manual"


@dataclass
class CaptchaInfo:
    """Detected CAPTCHA metadata."""
    found: bool = False
    captcha_type: CaptchaType = CaptchaType.UNKNOWN
    selector: str = ""
    img_selector: str = ""
    input_selector: str = ""
    sitekey: str = ""
    page_url: str = ""
    extra: dict = field(default_factory=dict)


@dataclass
class SolveResult:
    """Result of a CAPTCHA solve attempt."""
    success: bool = False
    answer: str = ""
    strategy_used: SolveStrategy = SolveStrategy.OCR
    confidence: float = 0.0
    cost: float = 0.0          # USD cost for paid services
    attempts: int = 0
    error: str = ""
    elapsed_ms: int = 0


# ---------------------------------------------------------------------------
# Default CAPTCHA CSS selectors (ordered by specificity)
# ---------------------------------------------------------------------------

CAPTCHA_SELECTORS: dict[CaptchaType, dict[str, str]] = {
    CaptchaType.TEXT_IMAGE: {
        "container": (
            'img[alt*="captcha" i], img[id*="captcha" i], img[src*="captcha" i], '
            'img[class*="captcha" i], .captcha-image, #captchaImage, '
            'img[alt*="verification" i], img[id*="verification" i]'
        ),
        "input": (
            'input[name*="captcha" i], input[id*="captcha" i], '
            'input[placeholder*="captcha" i], input[name*="captcha" i], '
            '#captcha, .captcha-input, input[name*="verif" i]'
        ),
    },
    CaptchaType.RECAPTCHA_V2: {
        "container": 'iframe[src*="recaptcha"], .g-recaptcha, #recaptcha, [data-sitekey]',
    },
    CaptchaType.RECAPTCHA_V3: {
        "container": 'script[src*="recaptcha/api.js?render="]',
    },
    CaptchaType.HCAPTCHA: {
        "container": 'iframe[src*="hcaptcha"], .h-captcha, [data-hcaptcha-sitekey]',
    },
    CaptchaType.SLIDER: {
        "container": (
            '.slider-captcha, .slide-verify, [class*="slider" i][class*="captcha" i], '
            '[class*="slide-verify"], .geetest_slider_button'
        ),
    },
    CaptchaType.IMAGE_SELECT: {
        "container": (
            'iframe[src*="recaptcha"][src*="bframe"], '
            'iframe[src*="hcaptcha"][src*="challenge"]'
        ),
    },
    CaptchaType.MATH: {
        "container": (
            '.math-captcha, [class*="math" i][class*="captcha" i], '
            'img[alt*="equation" i], img[alt*="calculate" i]'
        ),
        "input": 'input[name*="answer" i], input[name*="result" i], input[name*="math" i]',
    },
}


# ---------------------------------------------------------------------------
# Strategy implementations
# ---------------------------------------------------------------------------

class OcrStrategy:
    """Strategy 1: OCR-based text CAPTCHA solving via Tesseract."""

    @staticmethod
    def is_available() -> bool:
        try:
            import pytesseract
            from PIL import Image
            return True
        except ImportError:
            return False

    @staticmethod
    async def solve(page, img_selector: str, input_selector: str = "") -> SolveResult:
        result = SolveResult(strategy_used=SolveStrategy.OCR)
        if not OcrStrategy.is_available():
            result.error = "pytesseract/Pillow not installed"
            return result

        import pytesseract
        from PIL import Image, ImageFilter, ImageEnhance

        try:
            img_el = await page.query_selector(img_selector)
            if not img_el:
                result.error = f"CAPTCHA image not found: {img_selector}"
                return result

            screenshot = await img_el.screenshot()
            original = Image.open(io.BytesIO(screenshot))

            # Multiple preprocessing attempts
            pipelines = [
                # Pipeline A: simple grayscale + threshold
                lambda img: img.convert("L").point(lambda x: 0 if x < 128 else 255),
                # Pipeline B: contrast enhance + sharpen
                lambda img: ImageEnhance.Contrast(
                    ImageEnhance.Sharpness(img.convert("L")).enhance(2.0)
                ).enhance(2.0).point(lambda x: 0 if x < 100 else 255),
                # Pipeline C: resize up + denoise
                lambda img: (
                    img.convert("L")
                    .resize((img.width * 3, img.height * 3), Image.LANCZOS)
                    .filter(ImageFilter.MedianFilter(size=3))
                    .point(lambda x: 0 if x < 128 else 255)
                ),
                # Pipeline D: just grayscale, let Tesseract handle it
                lambda img: img.convert("L"),
            ]

            ocr_config = "--psm 7 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
            best_text = ""
            best_conf = 0.0

            for pipe in pipelines:
                try:
                    processed = pipe(original)
                    data = pytesseract.image_to_data(
                        processed, config=ocr_config, output_type=pytesseract.Output.DICT,
                    )
                    confs = [int(c) for c in data["conf"] if int(c) > 0]
                    texts = [t.strip() for t in data["text"] if t.strip()]
                    if texts:
                        text = "".join(texts)
                        avg_conf = sum(confs) / len(confs) if confs else 0
                        if avg_conf > best_conf and len(text) >= 3:
                            best_text = text
                            best_conf = avg_conf
                except Exception:
                    continue

            if best_text and len(best_text) >= 3:
                result.success = True
                result.answer = best_text
                result.confidence = best_conf / 100.0
                result.attempts = len(pipelines)

                # Fill the answer
                if input_selector:
                    inp = await page.query_selector(input_selector)
                    if inp:
                        await inp.fill(best_text)
                        logger.info(f"OCR solved: '{best_text}' (conf={best_conf:.0f}%)")
                else:
                    # Try common input selectors
                    for sel in CAPTCHA_SELECTORS[CaptchaType.TEXT_IMAGE]["input"].split(", "):
                        inp = await page.query_selector(sel.strip())
                        if inp:
                            await inp.fill(best_text)
                            break
            else:
                result.error = f"OCR failed — best: '{best_text}' conf={best_conf:.0f}"

        except Exception as e:
            result.error = f"OCR exception: {e}"
            logger.warning(result.error)

        return result


class AIStrategy:
    """Strategy 2: AI-powered CAPTCHA solving via AIBrain vision."""

    @staticmethod
    async def solve(page, img_selector: str = "", captcha_type: CaptchaType = CaptchaType.UNKNOWN,
                    page_url: str = "") -> SolveResult:
        result = SolveResult(strategy_used=SolveStrategy.AI)

        try:
            from src.ai.brain import AIBrain
            brain = AIBrain()
        except ImportError:
            result.error = "AIBrain not available"
            return result

        try:
            # Take screenshot of the whole page or the CAPTCHA element
            if img_selector:
                img_el = await page.query_selector(img_selector)
                if img_el:
                    screenshot = await img_el.screenshot()
                else:
                    screenshot = await page.screenshot(type="png")
            else:
                screenshot = await page.screenshot(type="png")

            import base64
            b64 = base64.b64encode(screenshot).decode()

            type_hint = {
                CaptchaType.TEXT_IMAGE: "This is a text CAPTCHA image. Read the characters shown.",
                CaptchaType.MATH: "This is a math CAPTCHA. Solve the equation and return the numeric answer.",
                CaptchaType.IMAGE_SELECT: "This is an image-selection CAPTCHA. Describe which images to select.",
                CaptchaType.SLIDER: "This is a slider CAPTCHA. Describe what action is needed.",
            }.get(captcha_type, "Identify and describe the CAPTCHA and how to solve it.")

            prompt = (
                f"{type_hint}\n\n"
                f"URL: {page_url}\n"
                "Return ONLY the answer text (no explanation). If text CAPTCHA, return the exact characters."
            )

            # Use the brain's API — build a vision-style message
            messages = [
                {"role": "system", "content": "You are a CAPTCHA solver. Return ONLY the solution, nothing else."},
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                ]},
            ]

            # Call via the brain's internal API method
            response = brain._call_api(messages, temperature=0.1)
            if response:
                answer = response.strip().split("\n")[0].strip()
                # Clean common prefixes
                for prefix in ["Answer:", "Solution:", "Text:", "Result:"]:
                    if answer.lower().startswith(prefix.lower()):
                        answer = answer[len(prefix):].strip()

                if answer and len(answer) <= 50:
                    result.success = True
                    result.answer = answer
                    result.confidence = 0.7
                    logger.info(f"AI solved CAPTCHA: '{answer}'")
                else:
                    result.error = f"AI returned unusable answer: '{answer[:100]}'"
            else:
                result.error = "AI API returned no response"

        except Exception as e:
            result.error = f"AI strategy exception: {e}"
            logger.warning(result.error)

        return result


class PaidServiceStrategy:
    """Strategy 3: 2Captcha / Anti-Captcha API integration."""

    SUPPORTED_SERVICES = ("2captcha", "anticaptcha")

    def __init__(self, service: str = "2captcha", api_key: str = "",
                 timeout: int = 120, poll_interval: int = 5):
        self.service = service
        self.api_key = api_key
        self.timeout = timeout
        self.poll_interval = poll_interval
        self._cost_tracker: list[float] = []

        if service == "2captcha":
            self.base_url = "https://2captcha.com"
        elif service == "anticaptcha":
            self.base_url = "https://api.anti-captcha.com"
        else:
            raise ValueError(f"Unsupported service: {service}. Use: {self.SUPPORTED_SERVICES}")

    @property
    def total_cost(self) -> float:
        return sum(self._cost_tracker)

    async def solve_text_captcha(self, image_bytes: bytes) -> SolveResult:
        """Solve a text/image CAPTCHA via the paid service."""
        import base64
        import httpx

        result = SolveResult(strategy_used=SolveStrategy.PAID_SERVICE)
        b64 = base64.b64encode(image_bytes).decode()
        start = time.monotonic()

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # Submit
                if self.service == "2captcha":
                    resp = await client.post(f"{self.base_url}/in.php", data={
                        "key": self.api_key,
                        "method": "base64",
                        "body": b64,
                        "json": 1,
                    })
                    data = resp.json()
                    if data.get("status") != 1:
                        result.error = f"Submit failed: {data.get('request', 'unknown')}"
                        return result
                    task_id = data["request"]
                else:  # anticaptcha
                    resp = await client.post(f"{self.base_url}/createTask", json={
                        "clientKey": self.api_key,
                        "task": {
                            "type": "ImageToTextTask",
                            "body": b64,
                        },
                    })
                    data = resp.json()
                    if data.get("errorId", 0) != 0:
                        result.error = f"Submit failed: {data.get('errorDescription', 'unknown')}"
                        return result
                    task_id = data["taskId"]

                # Poll for result
                elapsed = 0
                while elapsed < self.timeout:
                    await asyncio.sleep(self.poll_interval)
                    elapsed += self.poll_interval

                    if self.service == "2captcha":
                        resp = await client.get(f"{self.base_url}/res.php", params={
                            "key": self.api_key,
                            "action": "get",
                            "id": task_id,
                            "json": 1,
                        })
                        data = resp.json()
                        if data.get("status") == 1:
                            result.success = True
                            result.answer = data["request"]
                            result.confidence = 0.9
                            break
                        elif data.get("request") != "CAPCHA_NOT_READY":
                            result.error = f"Solve error: {data.get('request')}"
                            break
                    else:
                        resp = await client.post(f"{self.base_url}/getTaskResult", json={
                            "clientKey": self.api_key,
                            "taskId": task_id,
                        })
                        data = resp.json()
                        if data.get("status") == "ready":
                            result.success = True
                            result.answer = data["solution"]["text"]
                            result.confidence = 0.9
                            break
                        elif data.get("errorId", 0) != 0:
                            result.error = f"Solve error: {data.get('errorDescription')}"
                            break

                if not result.success and not result.error:
                    result.error = f"Timeout after {self.timeout}s"

                # Cost tracking (approximate)
                if result.success:
                    cost = 0.003  # ~$0.003 per text CAPTCHA
                    self._cost_tracker.append(cost)
                    result.cost = cost

        except Exception as e:
            result.error = f"Paid service exception: {e}"
            logger.warning(result.error)

        result.elapsed_ms = int((time.monotonic() - start) * 1000)
        return result

    async def solve_recaptcha_v2(self, page_url: str, sitekey: str) -> SolveResult:
        """Solve reCAPTCHA v2 via the paid service."""
        import httpx

        result = SolveResult(strategy_used=SolveStrategy.PAID_SERVICE)
        start = time.monotonic()

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                if self.service == "2captcha":
                    resp = await client.post(f"{self.base_url}/in.php", data={
                        "key": self.api_key,
                        "method": "userrecaptcha",
                        "googlekey": sitekey,
                        "pageurl": page_url,
                        "json": 1,
                    })
                    data = resp.json()
                    if data.get("status") != 1:
                        result.error = f"Submit failed: {data.get('request')}"
                        return result
                    task_id = data["request"]
                else:
                    resp = await client.post(f"{self.base_url}/createTask", json={
                        "clientKey": self.api_key,
                        "task": {
                            "type": "NoCaptchaTaskProxyless",
                            "websiteURL": page_url,
                            "websiteKey": sitekey,
                        },
                    })
                    data = resp.json()
                    if data.get("errorId", 0) != 0:
                        result.error = f"Submit failed: {data.get('errorDescription')}"
                        return result
                    task_id = data["taskId"]

                # Poll
                elapsed = 0
                while elapsed < self.timeout:
                    await asyncio.sleep(self.poll_interval)
                    elapsed += self.poll_interval

                    if self.service == "2captcha":
                        resp = await client.get(f"{self.base_url}/res.php", params={
                            "key": self.api_key, "action": "get", "id": task_id, "json": 1,
                        })
                        data = resp.json()
                        if data.get("status") == 1:
                            result.success = True
                            result.answer = data["request"]
                            result.confidence = 0.85
                            break
                        elif data.get("request") != "CAPCHA_NOT_READY":
                            result.error = f"Error: {data.get('request')}"
                            break
                    else:
                        resp = await client.post(f"{self.base_url}/getTaskResult", json={
                            "clientKey": self.api_key, "taskId": task_id,
                        })
                        data = resp.json()
                        if data.get("status") == "ready":
                            result.success = True
                            result.answer = data["solution"]["gRecaptchaResponse"]
                            result.confidence = 0.85
                            break

                if not result.success and not result.error:
                    result.error = f"Timeout after {self.timeout}s"

                if result.success:
                    cost = 0.003
                    self._cost_tracker.append(cost)
                    result.cost = cost

        except Exception as e:
            result.error = f"Paid service exception: {e}"

        result.elapsed_ms = int((time.monotonic() - start) * 1000)
        return result


class ManualStrategy:
    """Strategy 4: Manual fallback — screenshot, queue, notify user."""

    def __init__(self, queue_dir: str = "data/captcha_queue",
                 notifier: Optional[Callable] = None):
        self.queue_dir = Path(queue_dir)
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        self._notifier = notifier  # async callable(message, image_path)

    async def solve(self, page, captcha_info: CaptchaInfo,
                    timeout: int = 300) -> SolveResult:
        """Take screenshot, save to queue, notify user, wait for manual solve."""
        result = SolveResult(strategy_used=SolveStrategy.MANUAL)
        start = time.monotonic()

        try:
            # Take screenshot
            if captcha_info.img_selector:
                img_el = await page.query_selector(captcha_info.img_selector)
                if img_el:
                    screenshot = await img_el.screenshot()
                else:
                    screenshot = await page.screenshot(type="png")
            else:
                screenshot = await page.screenshot(type="png")

            # Save to queue
            ts = int(time.time())
            hash_short = hashlib.md5(screenshot).hexdigest()[:8]
            filename = f"captcha_{ts}_{hash_short}.png"
            filepath = self.queue_dir / filename
            filepath.write_bytes(screenshot)
            logger.info(f"CAPTCHA screenshot saved: {filepath}")

            # Notify user
            if self._notifier:
                try:
                    await self._notifier(
                        f"⚠️ CAPTCHA detected ({captcha_info.captcha_type.value}) — "
                        f"please solve manually. Screenshot: {filename}",
                        str(filepath),
                    )
                except Exception as e:
                    logger.warning(f"Notifier failed: {e}")

            # Wait for the CAPTCHA to be resolved (it disappears or a success indicator appears)
            try:
                await page.wait_for_function(
                    """() => {
                        const captcha = document.querySelector(
                            'img[alt*="captcha" i], .g-recaptcha, .h-captcha, .captcha-image'
                        );
                        const success = document.querySelector(
                            '.success, [class*="success"], .verified, [class*="verified"]'
                        );
                        return !captcha || success;
                    }""",
                    timeout=timeout * 1000,
                )
                result.success = True
                result.answer = "manual"
                result.confidence = 1.0
                logger.info("Manual CAPTCHA solved by user")
            except Exception:
                result.error = f"Manual solve timed out after {timeout}s"

        except Exception as e:
            result.error = f"Manual strategy exception: {e}"

        result.elapsed_ms = int((time.monotonic() - start) * 1000)
        return result


# ---------------------------------------------------------------------------
# Main handler
# ---------------------------------------------------------------------------

class CaptchaHandler:
    """Detect and solve CAPTCHAs with multi-strategy fallback chain.

    Default strategy order: OCR → AI → Paid Service → Manual
    """

    def __init__(self, config=None, notifier: Optional[Callable] = None):
        from src.core.config import AppConfig
        self.config = config or AppConfig.load()
        self._notifier = notifier
        self._paid_service: Optional[PaidServiceStrategy] = None
        self._manual: Optional[ManualStrategy] = None
        self._solve_history: list[SolveResult] = []

        # Configurable strategy order
        self.strategy_order: list[SolveStrategy] = [
            SolveStrategy.OCR,
            SolveStrategy.AI,
            SolveStrategy.PAID_SERVICE,
            SolveStrategy.MANUAL,
        ]

    # -- Configuration helpers -----------------------------------------------

    def configure_paid_service(self, service: str = "2captcha", api_key: str = "",
                                timeout: int = 120):
        """Enable paid CAPTCHA solving service."""
        if api_key:
            self._paid_service = PaidServiceStrategy(
                service=service, api_key=api_key, timeout=timeout,
            )
            logger.info(f"Paid CAPTCHA service configured: {service}")

    def set_strategy_order(self, order: list[SolveStrategy]):
        """Override default strategy execution order."""
        self.strategy_order = order

    def _get_manual(self) -> ManualStrategy:
        if self._manual is None:
            self._manual = ManualStrategy(
                queue_dir=str(Path(self.config.browser.screenshot_dir).parent / "captcha_queue"),
                notifier=self._notifier,
            )
        return self._manual

    # -- Detection -----------------------------------------------------------

    async def detect(self, page) -> CaptchaInfo:
        """Detect CAPTCHA presence on the page and return metadata."""
        info = CaptchaInfo(page_url=page.url)

        # Check each CAPTCHA type in priority order
        for ctype, selectors in CAPTCHA_SELECTORS.items():
            container_sel = selectors.get("container", "")
            if not container_sel:
                continue
            el = await page.query_selector(container_sel)
            if el:
                info.found = True
                info.captcha_type = ctype
                info.selector = container_sel
                info.input_selector = selectors.get("input", "")

                # Extract sitekey for reCAPTCHA / hCaptcha
                if ctype in (CaptchaType.RECAPTCHA_V2, CaptchaType.HCAPTCHA):
                    sitekey = await el.get_attribute("data-sitekey")
                    if sitekey:
                        info.sitekey = sitekey
                    elif ctype == CaptchaType.HCAPTCHA:
                        sitekey = await el.get_attribute("data-hcaptcha-sitekey")
                        if sitekey:
                            info.sitekey = sitekey

                # For text image CAPTCHAs, also find the image element specifically
                if ctype == CaptchaType.TEXT_IMAGE:
                    img_el = await page.query_selector(
                        'img[alt*="captcha" i], img[id*="captcha" i], img[src*="captcha" i], '
                        'img[alt*="verification" i], img[id*="verification" i]'
                    )
                    if img_el:
                        # Build a more specific selector
                        for attr in ("id", "alt", "src", "class"):
                            val = await img_el.get_attribute(attr)
                            if val and "captcha" in val.lower():
                                info.img_selector = f'img[{attr}="{val}"]'
                                break
                    if not info.img_selector:
                        info.img_selector = info.selector

                logger.info(f"CAPTCHA detected: {ctype.value} on {page.url}")
                return info

        return info

    # -- Solving -------------------------------------------------------------

    async def solve(self, page, captcha_info: Optional[CaptchaInfo] = None) -> SolveResult:
        """Detect and solve a CAPTCHA using the configured strategy chain.

        Returns the first successful SolveResult, or the last failure.
        """
        if captcha_info is None:
            captcha_info = await self.detect(page)

        if not captcha_info.found:
            return SolveResult(success=True, answer="", error="No CAPTCHA found")

        last_result = SolveResult(error="No strategy attempted")

        for strategy in self.strategy_order:
            logger.info(f"Trying strategy: {strategy.value} for {captcha_info.captcha_type.value}")
            last_result = await self._try_strategy(page, captcha_info, strategy)

            if last_result.success:
                self._solve_history.append(last_result)
                logger.info(
                    f"CAPTCHA solved via {strategy.value}: '{last_result.answer}' "
                    f"(conf={last_result.confidence:.0%}, cost=${last_result.cost:.4f})"
                )
                return last_result

            logger.warning(
                f"Strategy {strategy.value} failed: {last_result.error}"
            )

        self._solve_history.append(last_result)
        return last_result

    async def _try_strategy(self, page, info: CaptchaInfo,
                            strategy: SolveStrategy) -> SolveResult:
        """Execute a single strategy."""
        if strategy == SolveStrategy.OCR:
            if info.captcha_type not in (CaptchaType.TEXT_IMAGE, CaptchaType.MATH):
                return SolveResult(error=f"OCR not applicable for {info.captcha_type.value}")
            img_sel = info.img_selector or info.selector
            return await OcrStrategy.solve(page, img_sel, info.input_selector)

        elif strategy == SolveStrategy.AI:
            return await AIStrategy.solve(
                page, info.img_selector, info.captcha_type, info.page_url,
            )

        elif strategy == SolveStrategy.PAID_SERVICE:
            if self._paid_service is None:
                return SolveResult(error="No paid service configured")
            if info.captcha_type == CaptchaType.TEXT_IMAGE:
                img_sel = info.img_selector or info.selector
                img_el = await page.query_selector(img_sel)
                if img_el:
                    img_bytes = await img_el.screenshot()
                    return await self._paid_service.solve_text_captcha(img_bytes)
                return SolveResult(error="Cannot find CAPTCHA image for paid service")
            elif info.captcha_type == CaptchaType.RECAPTCHA_V2:
                return await self._paid_service.solve_recaptcha_v2(
                    info.page_url, info.sitekey,
                )
            else:
                return SolveResult(error=f"Paid service doesn't support {info.captcha_type.value}")

        elif strategy == SolveStrategy.MANUAL:
            return await self._get_manual().solve(page, info)

        return SolveResult(error=f"Unknown strategy: {strategy}")

    # -- Convenience ---------------------------------------------------------

    async def handle_navigation(self, page) -> SolveResult:
        """Detect + solve CAPTCHA during page navigation.

        Call this after page.goto() or any navigation that might trigger a CAPTCHA.
        """
        info = await self.detect(page)
        if not info.found:
            return SolveResult(success=True)
        return await self.solve(page, info)

    @property
    def total_cost(self) -> float:
        """Total USD spent on paid CAPTCHA solving."""
        if self._paid_service:
            return self._paid_service.total_cost
        return 0.0

    @property
    def solve_history(self) -> list[SolveResult]:
        return list(self._solve_history)

    def get_stats(self) -> dict:
        """Return solving statistics."""
        total = len(self._solve_history)
        solved = sum(1 for r in self._solve_history if r.success)
        by_strategy: dict[str, int] = {}
        for r in self._solve_history:
            key = r.strategy_used.value
            by_strategy[key] = by_strategy.get(key, 0) + 1
        return {
            "total_attempts": total,
            "solved": solved,
            "failed": total - solved,
            "success_rate": solved / total if total else 0.0,
            "total_cost_usd": self.total_cost,
            "by_strategy": by_strategy,
        }
