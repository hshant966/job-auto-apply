"""Learning API routes — failure analysis, strategy insights, event tracking."""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.api.app import get_db
from src.ai.self_learning import SelfLearningEngine

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Request models ──────────────────────────────────────────────────

class TrackEventRequest(BaseModel):
    application_id: str = ""
    outcome: str
    notes: str = ""
    job_id: str = ""
    portal: str = ""
    failure_type: str = ""
    reason: str = ""
    metadata: Optional[dict[str, Any]] = None


class AnalyzeRequest(BaseModel):
    days: int = 30


class EventQueryRequest(BaseModel):
    outcome: Optional[str] = None
    portal: Optional[str] = None
    days: int = 30
    limit: int = 100


# ── Endpoints ───────────────────────────────────────────────────────

@router.post("/analyze")
async def analyze_and_adjust(req: AnalyzeRequest):
    """Analyze failure patterns and generate strategy adjustments.

    Runs failure analysis over the last N days of learning events,
    then produces strategy recommendations (timing, portal picks, etc.).
    """
    engine = SelfLearningEngine(get_db())
    analysis = engine.analyze_failure_patterns(days=req.days)
    strategy = engine.adjust_strategy(analysis)

    return {
        "analysis": {
            "total_applications": analysis.total_applications,
            "total_failures": analysis.total_failures,
            "failure_rate": analysis.failure_rate,
            "failures_by_portal": analysis.failures_by_portal,
            "failures_by_type": analysis.failures_by_type,
            "common_rejection_reasons": analysis.common_rejection_reasons,
            "hourly_success_rates": {
                str(k): v for k, v in analysis.hourly_success_rates.items()
            },
            "best_hours": analysis.best_hours,
            "worst_hours": analysis.worst_hours,
            "portal_success_rates": analysis.portal_success_rates,
            "trends": analysis.trends,
        },
        "strategy": {
            "retry_timing_changes": strategy.retry_timing_changes,
            "portal_recommendations": strategy.portal_recommendations,
            "skip_recommendations": strategy.skip_recommendations,
            "credential_rotation": strategy.credential_rotation,
            "proxy_rotation": strategy.proxy_rotation,
            "max_retries_adjusted": strategy.max_retries_adjusted,
            "reasoning": strategy.reasoning,
        },
    }


@router.get("/insights")
async def get_insights(days: int = 7):
    """Get learning insights and weekly report.

    Returns a summary of recent application outcomes, portal performance,
    failure trends, and strategy recommendations.
    """
    engine = SelfLearningEngine(get_db())

    # Generate weekly report
    report = engine.generate_weekly_report()

    # Also fetch current strategy state
    strategy = engine.get_strategy_state()

    return {
        "report": {
            "period_start": report.period_start,
            "period_end": report.period_end,
            "total_applications": report.total_applications,
            "success_count": report.success_count,
            "failure_count": report.failure_count,
            "success_rate": report.success_rate,
            "top_failure_reasons": report.top_failure_reasons,
            "best_portals": report.best_portals,
            "worst_portals": report.worst_portals,
            "strategy_changes": report.strategy_changes,
            "insights": report.insights,
            "generated_at": report.generated_at,
        },
        "current_strategy": strategy,
    }


@router.post("/track")
async def track_event(req: TrackEventRequest):
    """Track an application outcome event.

    Feed this with results from apply operations so the learning engine
    can identify patterns and adjust strategy over time.
    """
    if not req.outcome:
        raise HTTPException(status_code=400, detail="outcome is required")

    engine = SelfLearningEngine(get_db())
    engine.track_outcome(
        application_id=req.application_id,
        outcome=req.outcome,
        notes=req.notes,
        job_id=req.job_id,
        portal=req.portal,
        failure_type=req.failure_type,
        reason=req.reason,
        metadata=req.metadata,
    )
    return {"status": "tracked", "outcome": req.outcome}


@router.post("/events")
async def query_events(req: EventQueryRequest):
    """Query learning events with optional filters."""
    engine = SelfLearningEngine(get_db())
    events = engine.get_events(
        outcome=req.outcome,
        portal=req.portal,
        days=req.days,
        limit=req.limit,
    )
    return {"events": events, "count": len(events)}


@router.get("/strategy")
async def get_strategy():
    """Get current persisted strategy state."""
    engine = SelfLearningEngine(get_db())
    strategy = engine.get_strategy_state()
    return {"strategy": strategy}


@router.post("/cleanup")
async def cleanup_old_events(days: int = 90):
    """Remove learning events older than N days."""
    engine = SelfLearningEngine(get_db())
    removed = engine.clear_old_events(days=days)
    return {"removed": removed, "older_than_days": days}
