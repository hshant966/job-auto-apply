"""Database manager — centralized SQLite operations."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

from .models import (
    Application, ApplicationStatus, Category, ContactInfo, Documents,
    Education, Experience, Gender, Job, JobPreferences, PersonalInfo,
    SalaryRange, UserProfile,
)

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL DEFAULT 'default',
    data_json TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    portal TEXT DEFAULT '',
    url TEXT DEFAULT '',
    url_hash TEXT NOT NULL UNIQUE,
    department TEXT DEFAULT '',
    qualification TEXT DEFAULT '',
    last_date TEXT,
    salary TEXT DEFAULT '',
    location TEXT DEFAULT '',
    description TEXT DEFAULT '',
    match_score INTEGER DEFAULT 0,
    discovered_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_jobs_portal ON jobs(portal);
CREATE INDEX IF NOT EXISTS idx_jobs_last_date ON jobs(last_date);
CREATE INDEX IF NOT EXISTS idx_jobs_url_hash ON jobs(url_hash);

CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'discovered',
    applied_date TEXT,
    reference_id TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (job_id) REFERENCES jobs(id)
);
CREATE INDEX IF NOT EXISTS idx_apps_status ON applications(status);
CREATE INDEX IF NOT EXISTS idx_apps_job_id ON applications(job_id);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS portal_sessions (
    portal TEXT PRIMARY KEY,
    cookies_json TEXT DEFAULT '[]',
    state_json TEXT DEFAULT '{}',
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ai_cache (
    key TEXT PRIMARY KEY,
    result TEXT NOT NULL,
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ai_cache_expires ON ai_cache(expires_at);

CREATE TABLE IF NOT EXISTS learning_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT,
    portal TEXT,
    failure_type TEXT,
    reason TEXT,
    timestamp REAL,
    metadata TEXT
);
"""


class Database:
    """Thread-safe SQLite database manager."""

    def __init__(self, db_path: str = "data/jobs.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()

    def _init_schema(self):
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def get_conn(self) -> sqlite3.Connection:
        return self._conn

    def close(self):
        self._conn.close()

    # ── Profile CRUD ─────────────────────────────────────────────────

    def create_profile(self, profile: UserProfile, name: str = "default") -> int:
        data = profile.model_dump_json()
        cur = self._conn.execute(
            "INSERT INTO profiles (name, data_json) VALUES (?, ?)", (name, data)
        )
        self._conn.commit()
        return cur.lastrowid

    def get_profile(self, profile_id: int = 1) -> Optional[UserProfile]:
        row = self._conn.execute(
            "SELECT data_json FROM profiles WHERE id = ?", (profile_id,)
        ).fetchone()
        if row is None:
            return None
        return UserProfile.model_validate_json(row["data_json"])

    def update_profile(self, profile_id: int, profile: UserProfile) -> bool:
        data = profile.model_dump_json()
        cur = self._conn.execute(
            "UPDATE profiles SET data_json = ?, updated_at = datetime('now') WHERE id = ?",
            (data, profile_id),
        )
        self._conn.commit()
        return cur.rowcount > 0

    def upsert_profile(self, profile: UserProfile, profile_id: int = 1) -> int:
        existing = self.get_profile(profile_id)
        if existing:
            self.update_profile(profile_id, profile)
            return profile_id
        return self.create_profile(profile)

    # ── Job CRUD ─────────────────────────────────────────────────────

    def save_job(self, job: Job) -> int:
        import hashlib
        url_hash = hashlib.sha256(job.url.encode()).hexdigest()[:32]
        cur = self._conn.execute(
            """INSERT OR IGNORE INTO jobs
               (title, portal, url, url_hash, department, qualification,
                last_date, salary, location, description, match_score)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (job.title, job.portal, job.url, url_hash, job.department,
             job.qualification, job.last_date.isoformat() if job.last_date else None,
             job.salary, job.location, job.description, job.match_score),
        )
        self._conn.commit()
        if cur.lastrowid:
            return cur.lastrowid
        # Already exists — get existing id
        row = self._conn.execute(
            "SELECT id FROM jobs WHERE url_hash = ?", (url_hash,)
        ).fetchone()
        return row["id"] if row else 0

    def get_job(self, job_id: int) -> Optional[Job]:
        row = self._conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return self._row_to_job(row) if row else None

    def search_jobs(
        self, portal: str = "", location: str = "", limit: int = 100, offset: int = 0
    ) -> list[Job]:
        clauses, params = [], []
        if portal:
            clauses.append("portal LIKE ?")
            params.append(f"%{portal}%")
        if location:
            clauses.append("location LIKE ?")
            params.append(f"%{location}%")
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"SELECT * FROM jobs{where} ORDER BY discovered_at DESC LIMIT ? OFFSET ?"
        params += [limit, offset]
        rows = self._conn.execute(sql, params).fetchall()
        return [self._row_to_job(r) for r in rows]

    def count_jobs(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]

    def upcoming_deadlines(self, days: int = 7) -> list[Job]:
        rows = self._conn.execute(
            """SELECT * FROM jobs
               WHERE last_date IS NOT NULL
                 AND last_date >= date('now')
                 AND last_date <= date('now', ?)
               ORDER BY last_date ASC""",
            (f"+{days} days",),
        ).fetchall()
        return [self._row_to_job(r) for r in rows]

    # ── Application CRUD ────────────────────────────────────────────

    def create_application(self, job_id: int, status: ApplicationStatus = ApplicationStatus.DRAFT) -> int:
        cur = self._conn.execute(
            """INSERT INTO applications (job_id, status, applied_date, updated_at)
               VALUES (?, ?, ?, ?)""",
            (job_id, status.value,
             datetime.now().isoformat() if status == ApplicationStatus.SUBMITTED else None,
             datetime.now().isoformat()),
        )
        self._conn.commit()
        return cur.lastrowid

    def get_application(self, app_id: int) -> Optional[Application]:
        row = self._conn.execute("SELECT * FROM applications WHERE id = ?", (app_id,)).fetchone()
        return self._row_to_app(row) if row else None

    def get_application_by_job(self, job_id: int) -> Optional[Application]:
        row = self._conn.execute(
            "SELECT * FROM applications WHERE job_id = ? ORDER BY created_at DESC LIMIT 1",
            (job_id,),
        ).fetchone()
        return self._row_to_app(row) if row else None

    def update_application_status(
        self, app_id: int, status: ApplicationStatus,
        reference_id: str = "", notes: str = ""
    ) -> bool:
        sets, params = ["status = ?", "updated_at = ?"], [status.value, datetime.now().isoformat()]
        if status == ApplicationStatus.SUBMITTED:
            sets.append("applied_date = ?")
            params.append(datetime.now().isoformat())
        if reference_id:
            sets.append("reference_id = ?")
            params.append(reference_id)
        if notes:
            sets.append("notes = ?")
            params.append(notes)
        params.append(app_id)
        cur = self._conn.execute(
            f"UPDATE applications SET {', '.join(sets)} WHERE id = ?", params
        )
        self._conn.commit()
        return cur.rowcount > 0

    def list_applications(
        self, status: Optional[ApplicationStatus] = None,
        limit: int = 100, offset: int = 0
    ) -> list[Application]:
        if status:
            rows = self._conn.execute(
                "SELECT * FROM applications WHERE status = ? ORDER BY updated_at DESC LIMIT ? OFFSET ?",
                (status.value, limit, offset),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM applications ORDER BY updated_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return [self._row_to_app(r) for r in rows]

    def application_stats(self) -> dict:
        rows = self._conn.execute(
            "SELECT status, COUNT(*) as cnt FROM applications GROUP BY status"
        ).fetchall()
        by_status = {r["status"]: r["cnt"] for r in rows}
        total = sum(by_status.values())
        submitted = by_status.get("submitted", 0) + by_status.get("confirmed", 0)
        return {
            "total_applications": total,
            "by_status": by_status,
            "submitted": submitted,
            "success_rate": round(submitted / total * 100, 1) if total else 0.0,
            "total_jobs": self.count_jobs(),
        }

    # ── Settings ────────────────────────────────────────────────────

    def get_setting(self, key: str, default: str = "") -> str:
        row = self._conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str):
        self._conn.execute(
            "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now'))",
            (key, value),
        )
        self._conn.commit()

    def get_all_settings(self) -> dict[str, str]:
        rows = self._conn.execute("SELECT key, value FROM settings").fetchall()
        return {r["key"]: r["value"] for r in rows}

    # ── Portal Sessions ─────────────────────────────────────────────

    def save_portal_session(self, portal: str, cookies: list, state: dict):
        self._conn.execute(
            """INSERT OR REPLACE INTO portal_sessions (portal, cookies_json, state_json, updated_at)
               VALUES (?, ?, ?, datetime('now'))""",
            (portal, json.dumps(cookies), json.dumps(state)),
        )
        self._conn.commit()

    def get_portal_session(self, portal: str) -> dict:
        row = self._conn.execute(
            "SELECT cookies_json, state_json FROM portal_sessions WHERE portal = ?", (portal,)
        ).fetchone()
        if not row:
            return {"cookies": [], "state": {}}
        return {
            "cookies": json.loads(row["cookies_json"]),
            "state": json.loads(row["state_json"]),
        }

    # ── AI Cache ────────────────────────────────────────────────────

    def cache_get(self, key: str) -> Optional[dict]:
        import time
        row = self._conn.execute(
            "SELECT result FROM ai_cache WHERE key = ? AND expires_at > ?",
            (key, time.time()),
        ).fetchone()
        return json.loads(row["result"]) if row else None

    def cache_set(self, key: str, result: dict, ttl_hours: int = 24):
        import time
        now = time.time()
        self._conn.execute(
            "INSERT OR REPLACE INTO ai_cache (key, result, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (key, json.dumps(result), now, now + ttl_hours * 3600),
        )
        self._conn.commit()

    # ── Helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _parse_date(raw: Optional[str]) -> Optional[date]:
        if not raw:
            return None
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(raw.strip(), fmt).date()
            except ValueError:
                continue
        return None

    @classmethod
    def _row_to_job(cls, row) -> Job:
        return Job(
            id=row["id"], title=row["title"], portal=row["portal"],
            url=row["url"], department=row["department"],
            qualification=row["qualification"],
            last_date=cls._parse_date(row["last_date"]),
            salary=row["salary"], location=row["location"],
            description=row["description"], match_score=row["match_score"] or 0,
            discovered_at=datetime.fromisoformat(row["discovered_at"]) if row["discovered_at"] else datetime.now(),
        )

    @staticmethod
    def _row_to_app(row) -> Application:
        return Application(
            id=row["id"], job_id=row["job_id"],
            status=ApplicationStatus(row["status"]),
            applied_date=datetime.fromisoformat(row["applied_date"]) if row["applied_date"] else None,
            reference_id=row["reference_id"], notes=row["notes"],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else datetime.now(),
        )
