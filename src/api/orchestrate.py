"""
Orchestration API routes — run, monitor, and control the full pipeline.

Exposes the Orchestrator via FastAPI endpoints following V2 patterns.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.api.app import get_db, get_config, get_browser

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Single global orchestrator instance (per-process) ──────────────
_orchestrator = None


def _get_orchestrator():
    """Get or create the singleton orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        from src.orchestrator import Orchestrator
        _orchestrator = Orchestrator(
            db=get_db(),
            browser_mgr=get_browser(),
            config=get_config(),
        )
    return _orchestrator


# ── Request / Response Models ──────────────────────────────────────

class RunRequest(BaseModel):
    """Parameters for a pipeline run."""
    profile_id: int = Field(default=1, description="User profile ID")
    portals: Optional[list[str]] = Field(
        default=None,
        description="Restrict to these portals (None = all)",
    )
    max_applications: int = Field(
        default=20, ge=1, le=100,
        description="Max jobs to apply to in this run",
    )
    min_match_score: int = Field(
        default=30, ge=0, le=100,
        description="Minimum AI match score to proceed",
    )
    skip_apply: bool = Field(
        default=False,
        description="Dry run — stop after match/prepare stages",
    )


class RunResponse(BaseModel):
    run_id: str
    stage: str
    started_at: str
    finished_at: str = ""
    total_jobs: int = 0
    scanned: int = 0
    matched: int = 0
    applied: int = 0
    failed: int = 0
    skipped: int = 0
    error_count: int = 0
    jobs: list[dict[str, Any]] = []


# ── Endpoints ──────────────────────────────────────────────────────

@router.post("/run", response_model=RunResponse)
async def start_pipeline_run(req: RunRequest):
    """Start a full pipeline run.

    Executes: scan → match → prepare → apply → track → learn

    Returns immediately with the run result. If you need async
    monitoring, use /status to poll progress.
    """
    orch = _get_orchestrator()

    if orch.is_running:
        raise HTTPException(
            status_code=409,
            detail="A pipeline run is already in progress. Stop it first or wait for completion.",
        )

    try:
        run = await orch.run(
            profile_id=req.profile_id,
            portals=req.portals,
            max_applications=req.max_applications,
            min_match_score=req.min_match_score,
            skip_apply=req.skip_apply,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error("Pipeline run failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {e}")

    return RunResponse(**run.summary())


@router.get("/status")
async def get_pipeline_status():
    """Check current pipeline status.

    Returns the in-progress run state, or the last completed run
    if nothing is currently running.
    """
    orch = _get_orchestrator()

    if orch.current_run and orch.is_running:
        run = orch.current_run
        return {
            "running": True,
            "run": run.summary(),
        }

    # Return last run from history
    if orch.history:
        last = orch.history[-1]
        return {
            "running": False,
            "last_run": last.summary(),
        }

    return {
        "running": False,
        "last_run": None,
        "message": "No pipeline runs yet.",
    }


@router.post("/stop")
async def stop_pipeline():
    """Stop a running pipeline gracefully.

    The pipeline will finish its current job and then halt.
    Partial results are preserved in the run history.
    """
    orch = _get_orchestrator()

    if not orch.is_running:
        raise HTTPException(
            status_code=400,
            detail="No pipeline is currently running.",
        )

    stopped = await orch.stop()
    return {
        "status": "stopping" if stopped else "already_stopped",
        "message": "Pipeline will stop after current job completes.",
    }


@router.get("/history")
async def get_pipeline_history(limit: int = 20):
    """Get past pipeline run history.

    Returns a list of completed runs with their summaries,
    most recent first.
    """
    orch = _get_orchestrator()
    runs = orch.history[-limit:] if orch.history else []
    runs.reverse()  # Most recent first

    return {
        "runs": [run.summary() for run in runs],
        "total": len(orch.history),
    }
