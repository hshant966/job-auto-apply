"""Configuration management — env vars + database settings."""

from __future__ import annotations

import logging
import os
import secrets
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TelegramConfig(BaseModel):
    bot_token: str = ""
    chat_id: str = ""


class AIConfig(BaseModel):
    provider: str = "openrouter"
    openrouter_api_key: str = ""
    openrouter_model: str = "meta-llama/llama-3.1-8b-instruct:free"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-haiku-20240307"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    custom_api_base: str = ""
    custom_api_key: str = ""
    custom_model: str = ""


class BrowserConfig(BaseModel):
    headless: bool = True
    stealth_enabled: bool = True
    data_dir: str = "data/browser_data"
    screenshot_dir: str = "data/screenshots"


class ScanConfig(BaseModel):
    interval_minutes: int = 120
    max_applications_per_run: int = 10
    min_match_score: int = 40
    rss_feeds: list[str] = Field(default_factory=lambda: [
        "https://www.employmentnews.gov.in/NewEmply/RSSFeed.aspx",
    ])


class ServerConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000
    secret_key: str = Field(default_factory=lambda: secrets.token_hex(32))


class AppConfig(BaseModel):
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    ai: AIConfig = Field(default_factory=AIConfig)
    browser: BrowserConfig = Field(default_factory=BrowserConfig)
    scan: ScanConfig = Field(default_factory=ScanConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    data_dir: str = "data"
    db_path: str = "data/jobs.db"
    log_level: str = "INFO"

    @classmethod
    def load(cls, env_file: str = ".env") -> "AppConfig":
        """Load config from .env file and environment variables."""
        # Load .env if exists
        env_path = Path(env_file)
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, value = line.partition("=")
                    key, value = key.strip(), value.strip()
                    if key and key not in os.environ:
                        os.environ[key] = value

        result = cls(
            telegram=TelegramConfig(
                bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
                chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
            ),
            ai=AIConfig(
                provider=os.getenv("AI_PROVIDER", "openrouter"),
                openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
                openrouter_model=os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct:free"),
                anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
                anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307"),
                openai_api_key=os.getenv("OPENAI_API_KEY", ""),
                openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                custom_api_base=os.getenv("AI_API_BASE_URL", ""),
                custom_api_key=os.getenv("AI_API_KEY", ""),
                custom_model=os.getenv("AI_MODEL", ""),
            ),
            browser=BrowserConfig(
                headless=os.getenv("HEADLESS", "true").lower() == "true",
                stealth_enabled=os.getenv("STEALTH_ENABLED", "true").lower() == "true",
                data_dir=os.getenv("BROWSER_DATA_DIR", "data/browser_data"),
                screenshot_dir=os.getenv("SCREENSHOT_DIR", "data/screenshots"),
            ),
            scan=ScanConfig(
                interval_minutes=int(os.getenv("SCAN_INTERVAL_MINUTES", "120")),
                max_applications_per_run=int(os.getenv("MAX_APPLICATIONS_PER_RUN", "10")),
                min_match_score=int(os.getenv("MIN_MATCH_SCORE", "40")),
            ),
            server=ServerConfig(
                host=os.getenv("HOST", "127.0.0.1"),
                port=int(os.getenv("PORT", "8000")),
                secret_key=os.getenv("SECRET_KEY", "") or secrets.token_hex(32),
            ),
            data_dir=os.getenv("DATA_DIR", "data"),
            db_path=os.getenv("DB_PATH", "data/jobs.db"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )

        if not os.getenv("SECRET_KEY"):
            logger.warning("SECRET_KEY env var not set — a random key was generated. "
                           "Sessions will not persist across restarts. "
                           "Set SECRET_KEY in your environment or .env file.")
        return result

    def get_portal_credentials(self, portal_name: str) -> Optional[dict]:
        """Get credentials for a portal from DB settings."""
        # This is a placeholder — credentials are stored in DB, not config
        return None

    def set_portal_password(self, portal_name: str, username: str, password: str):
        """Set portal credentials (placeholder — use DB settings)."""
        pass

    def save_to_env(self, env_file: str = ".env"):
        """Write current config to .env file."""
        lines = [
            "# JobAutoApply Configuration",
            f"AI_PROVIDER={self.ai.provider}",
            f"OPENROUTER_API_KEY={self.ai.openrouter_api_key}",
            f"OPENROUTER_MODEL={self.ai.openrouter_model}",
            f"ANTHROPIC_API_KEY={self.ai.anthropic_api_key}",
            f"ANTHROPIC_MODEL={self.ai.anthropic_model}",
            f"OPENAI_API_KEY={self.ai.openai_api_key}",
            f"OPENAI_MODEL={self.ai.openai_model}",
            f"AI_API_BASE_URL={self.ai.custom_api_base}",
            f"AI_API_KEY={self.ai.custom_api_key}",
            f"AI_MODEL={self.ai.custom_model}",
            f"TELEGRAM_BOT_TOKEN={self.telegram.bot_token}",
            f"TELEGRAM_CHAT_ID={self.telegram.chat_id}",
            f"HEADLESS={'true' if self.browser.headless else 'false'}",
            f"STEALTH_ENABLED={'true' if self.browser.stealth_enabled else 'false'}",
            f"SCAN_INTERVAL_MINUTES={self.scan.interval_minutes}",
            f"MAX_APPLICATIONS_PER_RUN={self.scan.max_applications_per_run}",
            f"MIN_MATCH_SCORE={self.scan.min_match_score}",
            f"HOST={self.server.host}",
            f"PORT={self.server.port}",
            f"SECRET_KEY={self.server.secret_key}",
            f"DB_PATH={self.db_path}",
            f"LOG_LEVEL={self.log_level}",
        ]
        Path(env_file).write_text("\n".join(lines) + "\n")
