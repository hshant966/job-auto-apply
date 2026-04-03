"""Session persistence — save/restore browser state via Database."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Optional

from playwright.async_api import BrowserContext

logger = logging.getLogger(__name__)

SESSION_EXPIRY_DAYS = 30


class SessionPersistence:
    """Manage persistent browser sessions backed by the central Database.

    V1 stored encrypted files on disk under ~/.job-auto-apply/sessions/.
    V2 delegates to Database.save_portal_session / get_portal_session so
    all state lives in a single SQLite file.
    """

    def __init__(self, db: Any) -> None:
        """Args:
        db: A ``src.core.database.Database`` instance (or compatible).
        """
        self._db = db

    # ── Full context save/restore ────────────────────────────────────

    async def save_session(
        self,
        portal: str,
        context: BrowserContext,
    ) -> None:
        """Capture cookies + storage state from *context* and persist to DB."""
        try:
            cookies = await context.cookies()
            state = await context.storage_state()
            self._db.save_portal_session(portal, cookies, state)
            logger.info(
                "Session saved for %s (%d cookies)", portal, len(cookies)
            )
        except Exception as exc:
            logger.error("Failed to save session '%s': %s", portal, exc)

    async def restore_session(self, portal: str) -> Optional[dict[str, Any]]:
        """Return the stored storage-state dict, or *None* if absent / expired."""
        session = self._db.get_portal_session(portal)
        if not session.get("cookies"):
            logger.debug("No saved session for '%s'", portal)
            return None

        # Expiry check via settings key
        ts_key = f"session_saved_at:{portal}"
        saved_at_str = self._db.get_setting(ts_key)
        if saved_at_str:
            try:
                saved_at = float(saved_at_str)
                age_days = (time.time() - saved_at) / 86400
                if age_days > SESSION_EXPIRY_DAYS:
                    logger.info(
                        "Session '%s' is %.0f days old — discarding",
                        portal,
                        age_days,
                    )
                    self.delete_session(portal)
                    return None
            except ValueError:
                pass

        logger.info(
            "Session restored for %s (%d cookies)",
            portal,
            len(session.get("cookies", [])),
        )
        return session

    # ── Cookie helpers ───────────────────────────────────────────────

    async def save_cookies(self, portal: str, cookies: list[dict]) -> None:
        """Persist *cookies* (Playwright format) for *portal*."""
        # Keep existing state if any
        existing = self._db.get_portal_session(portal)
        self._db.save_portal_session(portal, cookies, existing.get("state", {}))
        self._mark_timestamp(portal)
        logger.debug("Saved %d cookies for '%s'", len(cookies), portal)

    async def load_cookies(self, portal: str) -> list[dict]:
        """Return previously-saved cookies for *portal* (empty list if none)."""
        session = self._db.get_portal_session(portal)
        return session.get("cookies", [])

    # ── Lifecycle ────────────────────────────────────────────────────

    def delete_session(self, portal: str) -> bool:
        """Remove stored session for *portal*. Returns True if one existed."""
        session = self._db.get_portal_session(portal)
        if session.get("cookies") or session.get("state"):
            self._db.save_portal_session(portal, [], {})
            logger.info("Session deleted for '%s'", portal)
            return True
        return False

    def list_sessions(self) -> list[dict[str, Any]]:
        """Return summary of every stored portal session."""
        # portal_sessions table doesn't have a list-all helper, so query directly
        rows = self._db.get_conn().execute(
            "SELECT portal, updated_at FROM portal_sessions ORDER BY portal"
        ).fetchall()
        results = []
        for row in rows:
            portal = row["portal"]
            info: dict[str, Any] = {"portal": portal, "updated_at": row["updated_at"]}
            session = self._db.get_portal_session(portal)
            info["cookie_count"] = len(session.get("cookies", []))
            ts_key = f"session_saved_at:{portal}"
            saved_at_str = self._db.get_setting(ts_key)
            if saved_at_str:
                try:
                    age_days = (time.time() - float(saved_at_str)) / 86400
                    info["age_days"] = round(age_days, 1)
                    info["expired"] = age_days > SESSION_EXPIRY_DAYS
                except ValueError:
                    pass
            results.append(info)
        return results

    def cleanup_expired(self) -> int:
        """Delete sessions older than SESSION_EXPIRY_DAYS. Returns count removed."""
        cleaned = 0
        for info in self.list_sessions():
            if info.get("expired", False) and self.delete_session(info["portal"]):
                cleaned += 1
        if cleaned:
            logger.info("Cleaned up %d expired session(s)", cleaned)
        return cleaned

    # ── Internal ─────────────────────────────────────────────────────

    def _mark_timestamp(self, portal: str) -> None:
        self._db.set_setting(f"session_saved_at:{portal}", str(time.time()))
