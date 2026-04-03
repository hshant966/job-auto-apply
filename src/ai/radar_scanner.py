"""
Continuous Job Discovery Radar — multi-source RSS feed scanning.

Ports V1's radar_scanner.py to V2 patterns:
- Uses feedparser for RSS/Atom parsing
- Uses httpx for HTTP requests
- Integrates with V2's Database and Job model
- stdlib logging
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import feedparser
import httpx

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class ScanResult:
    """Result of a radar scan."""
    new_jobs: list[dict] = field(default_factory=list)
    total_found: int = 0
    duplicates_removed: int = 0
    sources_scanned: int = 0
    errors: list[str] = field(default_factory=list)
    scan_duration_seconds: float = 0.0
    timestamp: str = ""


# ---------------------------------------------------------------------------
# Default RSS feeds (India-focused)
# ---------------------------------------------------------------------------

DEFAULT_RSS_FEEDS: dict[str, str] = {
    "employment_news": "https://www.employmentnews.gov.in/NewEmp/Feed/rss.xml",
    "sarkari_result": "https://www.sarkariresult.com/feed/",
    "freejobalert": "https://www.freejobalert.com/feed/",
}


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------

_SKILLS = [
    "python", "java", "javascript", "react", "angular", "node.js",
    "sql", "aws", "docker", "kubernetes", "machine learning",
    "data science", "excel", "power bi", "tableau",
    "c", "c++", "c#", ".net", "php", "html", "css",
    "spring", "django", "flask", "mongodb", "mysql", "postgresql",
    "go", "rust", "scala", "kafka", "spark", "airflow",
    "devops", "ci/cd", "git", "linux", "agile", "scrum",
]

_DEADLINE_PATTERNS = [
    r"(?i)last date[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
    r"(?i)deadline[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
    r"(?i)apply before[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
    r"(?i)closing date[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
]

_EXPERIENCE_PATTERNS = [
    r"(\d+)\+?\s*(?:-\s*\d+)?\s*years?\s*(?:of\s*)?experience",
    r"(?i)experience[:\s]*(\d+)\+?\s*years?",
]

_GOV_CATEGORIES = {"general", "obc", "sc", "st", "ews", "pwd", "unreserved"}


def _extract_skills(text: str) -> list[str]:
    text_lower = text.lower()
    return [s for s in _SKILLS if s in text_lower]


def _extract_deadline(text: str) -> Optional[str]:
    for pat in _DEADLINE_PATTERNS:
        m = re.search(pat, text)
        if m:
            return m.group(1)
    return None


def _extract_experience(text: str) -> Optional[str]:
    for pat in _EXPERIENCE_PATTERNS:
        m = re.search(pat, text)
        if m:
            return f"{m.group(1)} years"
    return None


def _extract_category(text: str) -> str:
    text_lower = text.lower()
    for cat in _GOV_CATEGORIES:
        if cat in text_lower:
            return cat
    return ""


# ---------------------------------------------------------------------------
# RadarScanner
# ---------------------------------------------------------------------------

class RadarScanner:
    """Multi-source job discovery scanner.

    Scans RSS feeds and web sources for new postings, deduplicates
    against the V2 database, and prioritizes by deadline.

    Usage::

        scanner = RadarScanner(db)
        result = scanner.scan_all_sources(profile={"skills": ["python"]})
    """

    def __init__(
        self,
        db,
        rss_feeds: Optional[dict[str, str]] = None,
        timeout: int = 30,
    ):
        """
        Args:
            db: V2 Database instance.
            rss_feeds: Custom RSS feed dict {name: url}. Defaults to DEFAULT_RSS_FEEDS.
            timeout: HTTP timeout in seconds per source.
        """
        self._db = db
        self._feeds = rss_feeds or DEFAULT_RSS_FEEDS
        self._timeout = timeout

    # -------------------------------------------------------------------
    # Main scan
    # -------------------------------------------------------------------

    def scan_all_sources(self, profile: Optional[dict[str, Any]] = None) -> ScanResult:
        """Scan all configured sources for new jobs.

        Args:
            profile: Optional user profile dict for targeted scanning.

        Returns:
            ScanResult with discovered jobs and metadata.
        """
        from src.core.models import Job

        start = time.time()
        all_jobs: list[dict] = []
        errors: list[str] = []
        sources_scanned = 0

        # 1. RSS feeds
        for name, url in self._feeds.items():
            try:
                jobs = self._scan_rss(name, url)
                all_jobs.extend(jobs)
                sources_scanned += 1
            except Exception as e:
                errors.append(f"RSS {name}: {e}")
                logger.warning("RSS scan failed for %s: %s", name, e)

        # 2. Search-engine simulation (if profile available)
        if profile:
            try:
                search_jobs = self._scan_search(profile)
                all_jobs.extend(search_jobs)
                sources_scanned += 1
            except Exception as e:
                errors.append(f"Search: {e}")
                logger.warning("Search scan failed: %s", e)

        total_found = len(all_jobs)

        # Deduplicate against V2 database
        new_jobs = self._dedup(all_jobs)

        # Prioritize by deadline
        new_jobs = self._prioritize(new_jobs)

        duration = round(time.time() - start, 2)

        result = ScanResult(
            new_jobs=new_jobs,
            total_found=total_found,
            duplicates_removed=total_found - len(new_jobs),
            sources_scanned=sources_scanned,
            errors=errors,
            scan_duration_seconds=duration,
            timestamp=datetime.now().isoformat(),
        )

        # Save new jobs to V2 DB
        saved = 0
        for jdata in new_jobs:
            try:
                job = Job(
                    title=jdata.get("title", ""),
                    portal=jdata.get("portal", "radar"),
                    url=jdata.get("url", ""),
                    description=jdata.get("description", ""),
                    location=jdata.get("location", ""),
                    salary=jdata.get("salary", ""),
                )
                if jdata.get("last_date"):
                    from datetime import date as _date
                    try:
                        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
                            try:
                                job.last_date = _date.fromisoformat(
                                    datetime.strptime(jdata["last_date"], fmt).strftime("%Y-%m-%d")
                                )
                                break
                            except ValueError:
                                continue
                    except Exception:
                        pass
                if job.title and job.url:
                    self._db.save_job(job)
                    saved += 1
            except Exception as e:
                logger.warning("Failed to save job %s: %s", jdata.get("title"), e)

        logger.info(
            "Radar scan: %d found, %d new, %d saved, %d duplicates, %d errors in %.1fs",
            total_found, len(new_jobs), saved,
            result.duplicates_removed, len(errors), duration,
        )

        return result

    # -------------------------------------------------------------------
    # Source scanners
    # -------------------------------------------------------------------

    def _scan_rss(self, name: str, url: str) -> list[dict]:
        """Scan a single RSS/Atom feed."""
        jobs = []
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:100]:
                desc = entry.get("summary", "") or entry.get("description", "")
                desc_clean = re.sub(r"<[^>]+>", " ", desc).strip()

                job = {
                    "title": (entry.get("title", ""))[:200],
                    "description": desc_clean[:2000],
                    "url": entry.get("link", ""),
                    "portal": name,
                    "source_url": url,
                    "posted_date": entry.get("published", ""),
                    "skills": _extract_skills(desc_clean),
                    "last_date": _extract_deadline(desc_clean),
                    "experience": _extract_experience(desc_clean),
                    "category": _extract_category(desc_clean),
                }
                if job["title"]:
                    jobs.append(job)
        except Exception as e:
            logger.warning("RSS fetch failed for %s: %s", name, e)
        return jobs

    def _scan_search(self, profile: dict[str, Any]) -> list[dict]:
        """Simulate job search via web scraping."""
        jobs = []
        roles = profile.get("target_roles", []) or [profile.get("title", "software engineer")]

        for role in roles[:3]:
            query = f"latest {role} recruitment {datetime.now().year}"
            try:
                encoded = query.replace(" ", "+")
                search_urls = [
                    f"https://www.freejobalert.com/?s={encoded}",
                ]
                for surl in search_urls[:1]:
                    try:
                        resp = httpx.get(
                            surl,
                            headers={"User-Agent": "Mozilla/5.0 (compatible; JobRadar/2.0)"},
                            timeout=self._timeout,
                            follow_redirects=True,
                        )
                        html = resp.text[:50000]
                        titles = re.findall(r"<h[1-4][^>]*>(.*?)</h[1-4]>", html, re.IGNORECASE)
                        for t in titles[:5]:
                            clean = re.sub(r"<[^>]+>", "", t).strip()
                            if len(clean) > 10 and any(
                                w in clean.lower() for w in ["recruit", "job", "hiring", "post", "vacancy"]
                            ):
                                jobs.append({
                                    "title": clean[:200],
                                    "portal": "search",
                                    "url": surl,
                                    "skills": _extract_skills(clean),
                                })
                    except Exception:
                        pass
            except Exception as e:
                logger.debug("Search for '%s' failed: %s", role, e)

        return jobs

    # -------------------------------------------------------------------
    # Deduplication (uses V2 DB url_hash)
    # -------------------------------------------------------------------

    def _dedup(self, jobs: list[dict]) -> list[dict]:
        """Remove jobs whose URL already exists in the V2 database."""
        if not jobs:
            return []

        url_hashes: dict[str, dict] = {}
        for jdata in jobs:
            url = jdata.get("url", "")
            if url:
                h = hashlib.sha256(url.encode()).hexdigest()[:32]
                url_hashes[h] = jdata

        if not url_hashes:
            return []

        try:
            placeholders = ",".join("?" * len(url_hashes))
            rows = self._db._conn.execute(
                f"SELECT url_hash FROM jobs WHERE url_hash IN ({placeholders})",
                list(url_hashes.keys()),
            ).fetchall()
            seen = {r["url_hash"] for r in rows}
        except Exception:
            return list(url_hashes.values())

        return [j for h, j in url_hashes.items() if h not in seen]

    # -------------------------------------------------------------------
    # Prioritization
    # -------------------------------------------------------------------

    def _prioritize(self, jobs: list[dict]) -> list[dict]:
        """Sort jobs by application deadline (most urgent first)."""
        def _key(j: dict) -> float:
            dl = j.get("last_date", "")
            if not dl:
                return float("inf")
            for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%m/%d/%Y"):
                try:
                    return datetime.strptime(dl, fmt).timestamp()
                except ValueError:
                    continue
            return float("inf")

        return sorted(jobs, key=_key)

    # -------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------

    @property
    def sources(self) -> dict[str, str]:
        """Return configured RSS feed sources."""
        return dict(self._feeds)

    @property
    def scan_interval_hours(self) -> int:
        return 2
