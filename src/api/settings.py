"""Configuration management API."""
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from src.api.app import get_config, get_db

router = APIRouter()

# Whitelist of allowed setting keys for the update endpoint
ALLOWED_SETTING_KEYS = {
    "ai_provider",
    "ai_model",
    "openrouter_api_key",
    "anthropic_api_key",
    "openai_api_key",
    "headless",
    "stealth_enabled",
    "scan_interval",
    "max_applications",
    "min_match_score",
    "telegram_bot_token",
    "telegram_chat_id",
}


@router.get("/")
async def get_settings():
    """Get all application settings."""
    config = get_config()
    db = get_db()
    db_settings = db.get_all_settings()
    return {
        "ai_provider": config.ai.provider,
        "ai_model": config.ai.openrouter_model if config.ai.provider == "openrouter" else
                    config.ai.anthropic_model if config.ai.provider == "anthropic" else
                    config.ai.openai_model if config.ai.provider == "openai" else
                    config.ai.custom_model,
        "headless": config.browser.headless,
        "stealth_enabled": config.browser.stealth_enabled,
        "scan_interval": config.scan.interval_minutes,
        "max_applications": config.scan.max_applications_per_run,
        "min_match_score": config.scan.min_match_score,
        "telegram_configured": bool(config.telegram.bot_token),
        "host": config.server.host,
        "port": config.server.port,
        "db_path": config.db_path,
        "custom_settings": db_settings,
    }


@router.put("/")
async def update_settings(data: dict):
    """Update application settings."""
    # Validate: reject any keys not in the whitelist (custom_* is special-cased below)
    disallowed = {k for k in data if k not in ALLOWED_SETTING_KEYS and not k.startswith("custom_")}
    if disallowed:
        raise HTTPException(400, f"Unknown setting keys: {', '.join(sorted(disallowed))}")

    config = get_config()
    db = get_db()

    # Update config from data
    if "ai_provider" in data:
        config.ai.provider = data["ai_provider"]
    if "ai_model" in data:
        if config.ai.provider == "openrouter":
            config.ai.openrouter_model = data["ai_model"]
        elif config.ai.provider == "anthropic":
            config.ai.anthropic_model = data["ai_model"]
        elif config.ai.provider == "openai":
            config.ai.openai_model = data["ai_model"]
        else:
            config.ai.custom_model = data["ai_model"]
    if "openrouter_api_key" in data:
        config.ai.openrouter_api_key = data["openrouter_api_key"]
    if "anthropic_api_key" in data:
        config.ai.anthropic_api_key = data["anthropic_api_key"]
    if "openai_api_key" in data:
        config.ai.openai_api_key = data["openai_api_key"]
    if "headless" in data:
        config.browser.headless = data["headless"]
    if "stealth_enabled" in data:
        config.browser.stealth_enabled = data["stealth_enabled"]
    if "scan_interval" in data:
        config.scan.interval_minutes = data["scan_interval"]
    if "max_applications" in data:
        config.scan.max_applications_per_run = data["max_applications"]
    if "min_match_score" in data:
        config.scan.min_match_score = data["min_match_score"]
    if "telegram_bot_token" in data:
        config.telegram.bot_token = data["telegram_bot_token"]
    if "telegram_chat_id" in data:
        config.telegram.chat_id = data["telegram_chat_id"]

    # Save custom settings to DB
    for key, val in data.items():
        if key.startswith("custom_"):
            db.set_setting(key, str(val))

    # Save to .env
    try:
        config.save_to_env()
    except Exception:
        pass

    return {"ok": True, "message": "Settings updated"}


@router.post("/test-ai")
async def test_ai_connection():
    """Test the AI provider connection."""
    config = get_config()
    from src.ai.brain import AIBrain
    brain = AIBrain(config)
    # Simple test call
    response = brain._call_api([
        {"role": "user", "content": "Say 'connected' in one word."}
    ])
    if response:
        return {"ok": True, "response": response[:100]}
    return {"ok": False, "error": "No response from AI provider"}


@router.post("/test-telegram")
async def test_telegram():
    """Test Telegram notification."""
    config = get_config()
    if not config.telegram.bot_token:
        raise HTTPException(400, "Telegram not configured")
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{config.telegram.bot_token}/sendMessage",
                json={"chat_id": config.telegram.chat_id, "text": "🧪 JobAutoApply test message"},
            )
            if resp.status_code == 200:
                return {"ok": True}
            return {"ok": False, "error": resp.text[:200]}
    except Exception as e:
        raise HTTPException(500, f"Telegram test failed: {e}")
