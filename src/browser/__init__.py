"""Browser automation package — Playwright with stealth, CAPTCHA solving, and session persistence."""

from .browser_manager import BrowserManager
from .captcha_handler import CaptchaHandler, CaptchaType, SolveStrategy, CaptchaInfo, SolveResult

__all__ = [
    "BrowserManager",
    "CaptchaHandler",
    "CaptchaType",
    "SolveStrategy",
    "CaptchaInfo",
    "SolveResult",
]
