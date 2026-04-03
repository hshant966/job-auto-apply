"""
Self-Learning Engine — tracks application outcomes, analyzes failure patterns,
adjusts strategy, and generates learning reports.

Ported from V1 to use V2's Database for persistence.
"""

from __future__ import annotations

import json
import logging
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class Outcome:
    """Application outcome constants."""
    PENDING = "pending"
    APPLIED = "applied"
    VIEWED = "viewed"
    SHORTLISTED = "shortlisted"
    INTERVIEW = "interview"
    REJECTED = "rejected"
    OFFERED = "offered"
    ACCEPTED = "accepted"
    FAILED = "failed"  # technical failure (captcha, timeout, etc.)
    EXPIRED = "expired"


@dataclass
class FailureAnalysis:
    """Analysis of failure patterns across applications."""
    total_applications: int = 0
    total_failures: int = 0
    failure_rate: float = 0.0
    failures_by_portal: dict[str, int] = field(default_factory=dict)
    failures_by_type: dict[str, int] = field(default_factory=dict)
    common_rejection_reasons: list[str] = field(default_factory=list)
    hourly_success_rates: dict[int, float] = field(default_factory=dict)
    best_hours: list[int] = field(default_factory=list)
    worst_hours: list[int] = field(default_factory=list)
    portal_success_rates: dict[str, float] = field(default_factory=dict)
    trends: dict[str, str] = field(default_factory=dict)


@dataclass
class StrategyUpdate:
    """Recommended strategy adjustments."""
    retry_timing_changes: dict[str, str] = field(default_factory=dict)
    portal_recommendations: list[str] = field(default_factory=list)
    skip_recommendations: list[str] = field(default_factory=list)
    credential_rotation: bool = False
    proxy_rotation: bool = False
    max_retries_adjusted: Optional[int] = None
    reasoning: str = ""


@dataclass
class LearningReport:
    """Weekly learning report."""
    period_start: str = ""
    period_end: str = ""
    total_applications: int = 0
    success_count: int = 0
    failure_count: int = 0
    success_rate: float = 0.0
    top_failure_reasons: list[dict[str, Any]] = field(default_factory=list)
    best_portals: list[dict[str, Any]] = field(default_factory=list)
    worst_portals: list[dict[str, Any]] = field(default_factory=list)
    strategy_changes: list[str] = field(default_factory=list)
    insights: list[str] = field(default_factory=list)
    generated_at: str = ""


# ---------------------------------------------------------------------------
# SelfLearningEngine
# ---------------------------------------------------------------------------

# Schema for learning_events — initialized alongside V2's main schema
_LEARNING_SCHEMA = """
CREATE TABLE IF NOT EXISTS learning_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id TEXT DEFAULT '',
    job_id TEXT DEFAULT '',
    portal TEXT DEFAULT '',
    outcome TEXT NOT NULL,
    failure_type TEXT DEFAULT '',
    reason TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    hour_of_day INTEGER DEFAULT 0,
    day_of_week INTEGER DEFAULT 0,
    metadata TEXT DEFAULT '{}',
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_learn_outcome ON learning_events(outcome);
CREATE INDEX IF NOT EXISTS idx_learn_portal ON learning_events(portal);
CREATE INDEX IF NOT EXISTS idx_learn_created ON learning_events(created_at);

CREATE TABLE IF NOT EXISTS strategy_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at REAL
);
"""


class SelfLearningEngine:
    """Learning and self-correction engine for job applications.

    Tracks outcomes, identifies failure patterns, adjusts strategy,
    and generates reports to continuously improve application success.
    Uses V2's Database for persistence.
    """

    def __init__(self, db=None):
        """Initialize the learning engine.

        Args:
            db: V2 Database instance. If None, imports from app.
        """
        if db is None:
            from src.api.app import get_db
            db = get_db()
        self._db = db
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create learning tables if they don't exist."""
        self._db.get_conn().executescript(_LEARNING_SCHEMA)
        self._db.get_conn().commit()

    @property
    def _conn(self):
        return self._db.get_conn()

    # -------------------------------------------------------------------
    # Tracking
    # -------------------------------------------------------------------

    def track_outcome(
        self,
        application_id: str,
        outcome: str,
        notes: str = "",
        job_id: str = "",
        portal: str = "",
        failure_type: str = "",
        reason: str = "",
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Track an application outcome."""
        now = time.time()
        dt = datetime.fromtimestamp(now)

        self._conn.execute(
            "INSERT INTO learning_events "
            "(application_id, job_id, portal, outcome, failure_type, reason, "
            "notes, hour_of_day, day_of_week, metadata, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                application_id, job_id, portal, outcome,
                failure_type, reason, notes,
                dt.hour, dt.weekday(),
                json.dumps(metadata or {}), now,
            ),
        )
        self._conn.commit()
        logger.info(f"Tracked outcome: {outcome} for {application_id} on {portal}")

    # -------------------------------------------------------------------
    # Analysis
    # -------------------------------------------------------------------

    def analyze_failure_patterns(self, days: int = 30) -> FailureAnalysis:
        """Analyze failure patterns from learning events."""
        cutoff = time.time() - days * 86400

        rows = self._conn.execute(
            "SELECT portal, outcome, failure_type, reason, hour_of_day, notes "
            "FROM learning_events WHERE created_at >= ?",
            (cutoff,),
        ).fetchall()

        if not rows:
            return FailureAnalysis()

        total = len(rows)
        failures = [r for r in rows if r[1] in (Outcome.FAILED, Outcome.REJECTED, Outcome.EXPIRED)]
        total_failures = len(failures)

        # Failures by portal
        portal_counts = Counter(r[0] for r in rows if r[0])
        portal_failures = Counter(r[0] for r in failures if r[0])
        failures_by_portal = dict(portal_failures)

        # Portal success rates
        portal_success_rates = {}
        for portal, count in portal_counts.items():
            if portal:
                fail = portal_failures.get(portal, 0)
                portal_success_rates[portal] = round(1 - fail / count, 3) if count > 0 else 0

        # Failures by type
        failure_types = Counter(r[2] for r in failures if r[2])
        failures_by_type = dict(failure_types)

        # Common rejection reasons
        rejection_reasons = Counter(
            r[3] for r in failures if r[3] and r[1] == Outcome.REJECTED
        )
        common_rejections = [r for r, _ in rejection_reasons.most_common(5)]

        # Hourly success rates
        hour_totals = Counter(r[4] for r in rows)
        hour_successes = Counter(
            r[4] for r in rows if r[1] not in (Outcome.FAILED, Outcome.REJECTED)
        )
        hourly_rates = {}
        for hour in range(24):
            total_h = hour_totals.get(hour, 0)
            if total_h > 0:
                hourly_rates[hour] = round(hour_successes.get(hour, 0) / total_h, 3)

        # Best/worst hours
        sorted_hours = sorted(hourly_rates.items(), key=lambda x: x[1], reverse=True)
        best_hours = [h for h, r in sorted_hours[:3] if r > 0.5]
        worst_hours = [h for h, r in sorted_hours[-3:] if r < 0.5]

        # Trends
        trends = {}
        if total_failures / max(total, 1) > 0.5:
            trends["overall"] = "High failure rate — strategy adjustment recommended"
        if portal_failures:
            worst_portal = max(portal_failures, key=portal_failures.get)
            if portal_failures[worst_portal] > 5:
                trends["portal"] = f"Portal '{worst_portal}' has highest failure count"

        return FailureAnalysis(
            total_applications=total,
            total_failures=total_failures,
            failure_rate=round(total_failures / total, 3) if total > 0 else 0,
            failures_by_portal=failures_by_portal,
            failures_by_type=failures_by_type,
            common_rejection_reasons=common_rejections,
            hourly_success_rates=hourly_rates,
            best_hours=best_hours,
            worst_hours=worst_hours,
            portal_success_rates=portal_success_rates,
            trends=trends,
        )

    # -------------------------------------------------------------------
    # Strategy adjustment
    # -------------------------------------------------------------------

    def adjust_strategy(self, analysis: Optional[FailureAnalysis] = None) -> StrategyUpdate:
        """Generate strategy adjustments based on failure analysis."""
        if analysis is None:
            analysis = self.analyze_failure_patterns()

        update = StrategyUpdate()
        reasons = []

        # 1. Retry timing
        if analysis.best_hours:
            update.retry_timing_changes["apply_during"] = (
                f"Best hours: {', '.join(str(h) + ':00' for h in analysis.best_hours)}"
            )
            reasons.append(f"Success rate highest at hours {analysis.best_hours}")
        if analysis.worst_hours:
            update.retry_timing_changes["avoid"] = (
                f"Worst hours: {', '.join(str(h) + ':00' for h in analysis.worst_hours)}"
            )

        # 2. Portal recommendations
        for portal, rate in sorted(
            analysis.portal_success_rates.items(), key=lambda x: x[1]
        ):
            if rate < 0.3 and analysis.failures_by_portal.get(portal, 0) > 3:
                update.skip_recommendations.append(
                    f"Consider skipping '{portal}' (success rate: {rate:.0%})"
                )
            elif rate > 0.7:
                update.portal_recommendations.append(
                    f"Prioritize '{portal}' (success rate: {rate:.0%})"
                )

        # 3. Failure type handling
        if analysis.failures_by_type.get("captcha", 0) > 5:
            update.credential_rotation = True
            reasons.append("Frequent CAPTCHA failures — may need credential/proxy rotation")
        if analysis.failures_by_type.get("timeout", 0) > 5:
            update.proxy_rotation = True
            reasons.append("Frequent timeouts — consider proxy rotation or off-peak timing")
        if analysis.failures_by_type.get("login_error", 0) > 3:
            update.credential_rotation = True
            reasons.append("Login errors detected — credential refresh recommended")

        # 4. Overall failure rate
        if analysis.failure_rate > 0.6:
            update.max_retries_adjusted = 3
            reasons.append("High failure rate — reducing retry attempts to save resources")

        update.reasoning = "; ".join(reasons) if reasons else "No major adjustments needed."

        # Persist strategy state
        self._save_strategy_state(update)
        return update

    def _save_strategy_state(self, update: StrategyUpdate) -> None:
        """Persist strategy state to DB."""
        state = {
            "retry_timing": update.retry_timing_changes,
            "portal_recs": update.portal_recommendations,
            "skip_recs": update.skip_recommendations,
            "cred_rotation": update.credential_rotation,
            "proxy_rotation": update.proxy_rotation,
        }
        self._conn.execute(
            "INSERT OR REPLACE INTO strategy_state (key, value, updated_at) "
            "VALUES (?, ?, ?)",
            ("current_strategy", json.dumps(state), time.time()),
        )
        self._conn.commit()

    def get_strategy_state(self) -> Optional[dict[str, Any]]:
        """Get the current persisted strategy state."""
        row = self._conn.execute(
            "SELECT value FROM strategy_state WHERE key = 'current_strategy'"
        ).fetchone()
        if row:
            return json.loads(row[0])
        return None

    # -------------------------------------------------------------------
    # Weekly report
    # -------------------------------------------------------------------

    def generate_weekly_report(self) -> LearningReport:
        """Generate a weekly learning report."""
        now = datetime.now()
        period_start = now - timedelta(days=7)
        cutoff = period_start.timestamp()

        rows = self._conn.execute(
            "SELECT portal, outcome, failure_type, reason, notes "
            "FROM learning_events WHERE created_at >= ?",
            (cutoff,),
        ).fetchall()

        total = len(rows)
        successes = [
            r for r in rows
            if r[1] in (Outcome.APPLIED, Outcome.SHORTLISTED, Outcome.INTERVIEW, Outcome.OFFERED)
        ]
        failures = [r for r in rows if r[1] in (Outcome.FAILED, Outcome.REJECTED)]

        # Top failure reasons
        failure_reasons = Counter(r[3] for r in failures if r[3])
        top_failures = [
            {"reason": reason, "count": count}
            for reason, count in failure_reasons.most_common(5)
        ]

        # Portal analysis
        portal_totals = Counter(r[0] for r in rows if r[0])
        portal_success = Counter(r[0] for r in successes if r[0])

        best_portals = []
        worst_portals = []
        for portal, total_p in portal_totals.items():
            if portal and total_p >= 3:
                rate = portal_success.get(portal, 0) / total_p
                entry = {"portal": portal, "success_rate": round(rate, 2), "total": total_p}
                if rate >= 0.5:
                    best_portals.append(entry)
                else:
                    worst_portals.append(entry)

        best_portals.sort(key=lambda x: x["success_rate"], reverse=True)
        worst_portals.sort(key=lambda x: x["success_rate"])

        # Insights
        insights = []
        if total == 0:
            insights.append("No applications tracked this week.")
        else:
            success_rate = len(successes) / total
            if success_rate > 0.7:
                insights.append(f"Strong week! {success_rate:.0%} application success rate.")
            elif success_rate < 0.3:
                insights.append(f"Low success rate ({success_rate:.0%}). Review strategy adjustments.")
            if failure_reasons:
                top_reason = failure_reasons.most_common(1)[0]
                insights.append(f"Most common failure: '{top_reason[0]}' ({top_reason[1]} times)")
            if worst_portals:
                insights.append(f"Consider reducing usage of: {worst_portals[0]['portal']}")

        # Strategy changes from current state
        strategy = self.get_strategy_state()
        strategy_changes = []
        if strategy:
            if strategy.get("skip_recs"):
                strategy_changes.extend(strategy["skip_recs"])
            if strategy.get("portal_recs"):
                strategy_changes.extend(strategy["portal_recs"])

        return LearningReport(
            period_start=period_start.strftime("%Y-%m-%d"),
            period_end=now.strftime("%Y-%m-%d"),
            total_applications=total,
            success_count=len(successes),
            failure_count=len(failures),
            success_rate=round(len(successes) / total, 3) if total > 0 else 0,
            top_failure_reasons=top_failures,
            best_portals=best_portals[:5],
            worst_portals=worst_portals[:5],
            strategy_changes=strategy_changes,
            insights=insights,
            generated_at=now.isoformat(),
        )

    # -------------------------------------------------------------------
    # Query & maintenance
    # -------------------------------------------------------------------

    def get_events(
        self,
        outcome: Optional[str] = None,
        portal: Optional[str] = None,
        days: int = 30,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Query learning events with filters."""
        cutoff = time.time() - days * 86400
        conditions = ["created_at >= ?"]
        params: list = [cutoff]

        if outcome:
            conditions.append("outcome = ?")
            params.append(outcome)
        if portal:
            conditions.append("portal = ?")
            params.append(portal)

        query = (
            "SELECT application_id, job_id, portal, outcome, failure_type, "
            "reason, notes, hour_of_day, metadata, created_at "
            f"FROM learning_events WHERE {' AND '.join(conditions)} "
            "ORDER BY created_at DESC LIMIT ?"
        )
        params.append(limit)

        rows = self._conn.execute(query, params).fetchall()
        return [
            {
                "application_id": r[0], "job_id": r[1], "portal": r[2],
                "outcome": r[3], "failure_type": r[4], "reason": r[5],
                "notes": r[6], "hour": r[7],
                "metadata": json.loads(r[8] or "{}"),
                "timestamp": r[9],
            }
            for r in rows
        ]

    def clear_old_events(self, days: int = 90) -> int:
        """Remove events older than specified days."""
        cutoff = time.time() - days * 86400
        cur = self._conn.execute("DELETE FROM learning_events WHERE created_at < ?", (cutoff,))
        self._conn.commit()
        return cur.rowcount
