"""
Pipeline Orchestrator — coordinates the full job application pipeline.

Pipeline stages:
  scan (radar) → match (brain) → prepare (resume optimizer) → apply (adapters) → track (database) → learn (self_learning)

Design:
  - Class-based, callable from API or CLI
  - Async pipeline with per-job retry logic
  - Progress tracking via shared state
  - Graceful stop via asyncio.Event
  - stdlib logging, no new dependencies
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ── Enums & Models ──────────────────────────────────────────────────

class PipelineStage(str, Enum):
    IDLE = "idle"
    SCANNING = "scanning"
    MATCHING = "matching"
    PREPARING = "preparing"
    APPLYING = "applying"
    TRACKING = "tracking"
    LEARNING = "learning"
    DONE = "done"
    STOPPED = "stopped"
    ERROR = "error"


class JobPipelineStatus(str, Enum):
    QUEUED = "queued"
    SCANNING = "scanning"
    MATCHED = "matched"
    SKIPPED = "skipped"
    PREPARING = "preparing"
    APPLYING = "applying"
    APPLIED = "applied"
    FAILED = "failed"
    DEFERRED = "deferred"


@dataclass
class JobProgress:
    """Per-job progress within the pipeline."""
    job_id: int = 0
    title: str = ""
    portal: str = ""
    status: JobPipelineStatus = JobPipelineStatus.QUEUED
    match_score: int = 0
    error: str = ""
    retries: int = 0
    started_at: float = 0.0
    finished_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "title": self.title,
            "portal": self.portal,
            "status": self.status.value,
            "match_score": self.match_score,
            "error": self.error,
            "retries": self.retries,
            "duration_seconds": round(self.finished_at - self.started_at, 2) if self.finished_at else 0,
        }


@dataclass
class PipelineRun:
    """Full pipeline run state."""
    run_id: str = ""
    stage: PipelineStage = PipelineStage.IDLE
    started_at: str = ""
    finished_at: str = ""
    total_jobs: int = 0
    scanned: int = 0
    matched: int = 0
    applied: int = 0
    failed: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)
    job_progress: list[JobProgress] = field(default_factory=list)

    def summary(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "stage": self.stage.value,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "total_jobs": self.total_jobs,
            "scanned": self.scanned,
            "matched": self.matched,
            "applied": self.applied,
            "failed": self.failed,
            "skipped": self.skipped,
            "error_count": len(self.errors),
            "jobs": [jp.to_dict() for jp in self.job_progress],
        }


# ── Orchestrator ────────────────────────────────────────────────────

class Orchestrator:
    """Main pipeline orchestrator.

    Coordinates: scan → match → prepare → apply → track → learn

    Usage from API::

        orch = Orchestrator(db, browser_mgr, config)
        run = await orch.run(profile_id=1)

    Usage from CLI::

        orch = Orchestrator(db, browser_mgr, config)
        asyncio.run(orch.run(profile_id=1))
    """

    MAX_RETRIES = 3
    RETRY_DELAY_SECONDS = 5

    def __init__(self, db, browser_mgr=None, config=None):
        """
        Args:
            db: V2 Database instance.
            browser_mgr: BrowserManager instance (optional, needed for apply stage).
            config: AppConfig instance (optional).
        """
        self._db = db
        self._browser_mgr = browser_mgr
        self._config = config

        # Lazy-loaded modules
        self._brain = None
        self._radar = None
        self._resume_optimizer = None
        self._learning_engine = None

        # Pipeline state
        self._current_run: Optional[PipelineRun] = None
        self._stop_event = asyncio.Event()
        self._run_history: list[PipelineRun] = []

    # ── Lazy module loaders ───────────────────────────────────────

    def _get_brain(self):
        if self._brain is None:
            from src.ai.brain import AIBrain
            self._brain = AIBrain(self._config)
        return self._brain

    def _get_radar(self):
        if self._radar is None:
            from src.ai.radar_scanner import RadarScanner
            self._radar = RadarScanner(db=self._db)
        return self._radar

    def _get_resume_optimizer(self):
        if self._resume_optimizer is None:
            from src.ai.resume_optimizer import ResumeOptimizer
            brain = self._get_brain()
            self._resume_optimizer = ResumeOptimizer(
                db_path=self._config.db_path if self._config else None,
                brain=brain,
            )
        return self._resume_optimizer

    def _get_learning_engine(self):
        if self._learning_engine is None:
            from src.ai.self_learning import SelfLearningEngine
            self._learning_engine = SelfLearningEngine(db=self._db)
        return self._learning_engine

    def _get_adapter(self, portal: str):
        """Get an adapter instance for a portal."""
        from src.adapters import ADAPTER_REGISTRY
        adapter_cls = ADAPTER_REGISTRY.get(portal.lower())
        if adapter_cls is None:
            return None
        return adapter_cls(config=self._config)

    # ── Public API ────────────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        return self._current_run is not None and self._current_run.stage not in (
            PipelineStage.DONE, PipelineStage.STOPPED, PipelineStage.ERROR
        )

    @property
    def current_run(self) -> Optional[PipelineRun]:
        return self._current_run

    @property
    def history(self) -> list[PipelineRun]:
        return list(self._run_history)

    async def run(
        self,
        profile_id: int = 1,
        portals: Optional[list[str]] = None,
        max_applications: int = 20,
        min_match_score: int = 30,
        skip_apply: bool = False,
    ) -> PipelineRun:
        """Execute the full pipeline.

        Args:
            profile_id: User profile ID to use.
            portals: Restrict apply stage to these portals (None = all).
            max_applications: Max jobs to apply to in one run.
            min_match_score: Minimum match score to proceed with application.
            skip_apply: If True, stop after match/prepare (dry run).

        Returns:
            PipelineRun with full results.
        """
        if self.is_running:
            raise RuntimeError("Pipeline is already running. Stop it first.")

        run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self._stop_event.clear()
        self._current_run = PipelineRun(
            run_id=run_id,
            stage=PipelineStage.SCANNING,
            started_at=datetime.now().isoformat(),
        )

        logger.info("Pipeline %s started (profile=%d, max_apps=%d, min_score=%d)",
                     run_id, profile_id, max_applications, min_match_score)

        try:
            # Load profile
            profile = self._db.get_profile(profile_id)
            if profile is None:
                raise ValueError(f"Profile {profile_id} not found")
            profile_dict = profile.model_dump()

            # ── Stage 1: SCAN ──────────────────────────────────────
            self._current_run.stage = PipelineStage.SCANNING
            scan_result = await self._stage_scan(profile_dict)
            self._current_run.scanned = scan_result.get("new_jobs", 0)

            if self._stop_event.is_set():
                return self._finish(PipelineStage.STOPPED)

            # ── Stage 2: MATCH ─────────────────────────────────────
            self._current_run.stage = PipelineStage.MATCHING
            matched_jobs = await self._stage_match(min_match_score, profile_dict)
            self._current_run.matched = len(matched_jobs)
            self._current_run.total_jobs = len(matched_jobs)

            if self._stop_event.is_set():
                return self._finish(PipelineStage.STOPPED)

            if skip_apply:
                logger.info("Dry run — skipping apply/track/learn stages")
                return self._finish(PipelineStage.DONE)

            # Limit to max_applications
            to_apply = matched_jobs[:max_applications]

            # ── Stage 3-5: PREPARE → APPLY → TRACK (per job) ──────
            self._current_run.stage = PipelineStage.APPLYING

            for jp in to_apply:
                if self._stop_event.is_set():
                    break

                # Prepare
                jp.status = JobPipelineStatus.PREPARING
                await self._stage_prepare(jp, profile_dict)

                if self._stop_event.is_set():
                    break

                # Apply (with retries)
                applied = await self._stage_apply_with_retries(jp, profile_dict, portals)

                # Track
                await self._stage_track(jp, applied)

            self._current_run.applied = sum(
                1 for jp in self._current_run.job_progress
                if jp.status == JobPipelineStatus.APPLIED
            )
            self._current_run.failed = sum(
                1 for jp in self._current_run.job_progress
                if jp.status == JobPipelineStatus.FAILED
            )
            self._current_run.skipped = sum(
                1 for jp in self._current_run.job_progress
                if jp.status == JobPipelineStatus.SKIPPED
            )

            if self._stop_event.is_set():
                return self._finish(PipelineStage.STOPPED)

            # ── Stage 6: LEARN ─────────────────────────────────────
            self._current_run.stage = PipelineStage.LEARNING
            await self._stage_learn()

            return self._finish(PipelineStage.DONE)

        except Exception as e:
            logger.error("Pipeline %s failed: %s", run_id, e, exc_info=True)
            self._current_run.errors.append(f"Pipeline error: {e}")
            return self._finish(PipelineStage.ERROR)

    async def stop(self) -> bool:
        """Signal the pipeline to stop gracefully."""
        if not self.is_running:
            return False
        logger.info("Pipeline stop requested")
        self._stop_event.set()
        return True

    # ── Pipeline Stages ───────────────────────────────────────────

    async def _stage_scan(self, profile: dict) -> dict:
        """Stage 1: Scan for new jobs via radar."""
        logger.info("Stage: SCANNING")
        radar = self._get_radar()
        try:
            result = await asyncio.to_thread(radar.scan_all_sources, profile=profile)
            logger.info("Scan complete: %d found, %d new", result.total_found, len(result.new_jobs))
            return {"new_jobs": len(result.new_jobs), "total_found": result.total_found}
        except Exception as e:
            err = f"Scan failed: {e}"
            logger.error(err)
            self._current_run.errors.append(err)
            return {"new_jobs": 0, "total_found": 0}

    async def _stage_match(self, min_score: int, profile: dict) -> list[JobProgress]:
        """Stage 2: Score unprocessed jobs against the profile."""
        logger.info("Stage: MATCHING (min_score=%d)", min_score)
        brain = self._get_brain()

        # Get jobs without applications (unprocessed)
        all_jobs = self._db.search_jobs(limit=200)
        applied_job_ids = set()
        for app in self._db.list_applications(limit=500):
            applied_job_ids.add(app.job_id)

        unprocessed = [j for j in all_jobs if j.id and j.id not in applied_job_ids]
        logger.info("Found %d unprocessed jobs to match", len(unprocessed))

        matched: list[JobProgress] = []
        for job in unprocessed:
            if self._stop_event.is_set():
                break

            job_dict = job.model_dump()
            try:
                score_result = await asyncio.to_thread(
                    brain.analyze_job_match, job_dict, profile
                )
            except Exception as e:
                logger.warning("Match failed for job %d: %s", job.id, e)
                continue

            # Update match score in DB
            if job.id:
                self._db.get_conn().execute(
                    "UPDATE jobs SET match_score = ? WHERE id = ?",
                    (score_result.score, job.id),
                )
                self._db.get_conn().commit()

            if score_result.score >= min_score:
                jp = JobProgress(
                    job_id=job.id or 0,
                    title=job.title,
                    portal=job.portal,
                    status=JobPipelineStatus.MATCHED,
                    match_score=score_result.score,
                )
                matched.append(jp)
                self._current_run.job_progress.append(jp)

        # Sort by score descending
        matched.sort(key=lambda x: x.match_score, reverse=True)
        logger.info("Matched %d jobs above threshold %d", len(matched), min_score)
        return matched

    async def _stage_prepare(self, jp: JobProgress, profile: dict) -> None:
        """Stage 3: Prepare resume for this job."""
        logger.debug("Stage: PREPARE for job %d (%s)", jp.job_id, jp.title)
        optimizer = self._get_resume_optimizer()

        try:
            job = self._db.get_job(jp.job_id)
            if job is None:
                jp.status = JobPipelineStatus.FAILED
                jp.error = "Job not found in DB"
                return

            # If resume file exists, optimize it
            resume_path = profile.get("documents", {}).get("resume_path", "")
            if resume_path:
                from pathlib import Path
                if Path(resume_path).exists():
                    resume_data = await asyncio.to_thread(optimizer.parse_resume, resume_path)
                    optimized = await asyncio.to_thread(
                        optimizer.optimize_for_job,
                        job.description,
                        resume_data,
                    )
                    logger.info(
                        "Resume optimized for job %d: %d changes, ATS %d→%d",
                        jp.job_id, len(optimized.changes),
                        optimized.ats_score_before, optimized.ats_score_after,
                    )
        except Exception as e:
            logger.warning("Resume optimization failed for job %d: %s", jp.job_id, e)
            # Non-fatal — continue with original resume

    async def _stage_apply_with_retries(
        self, jp: JobProgress, profile: dict, portals: Optional[list[str]]
    ) -> bool:
        """Stage 4: Apply to the job with retry logic."""
        # Check portal filter
        if portals and jp.portal.lower() not in [p.lower() for p in portals]:
            jp.status = JobPipelineStatus.SKIPPED
            jp.error = f"Portal '{jp.portal}' not in allowed list"
            return False

        # Get adapter
        adapter = self._get_adapter(jp.portal)
        if adapter is None:
            jp.status = JobPipelineStatus.SKIPPED
            jp.error = f"No adapter for portal '{jp.portal}'"
            return False

        job = self._db.get_job(jp.job_id)
        if job is None:
            jp.status = JobPipelineStatus.FAILED
            jp.error = "Job not found"
            return False

        # Skip expired jobs
        if job.is_expired:
            jp.status = JobPipelineStatus.SKIPPED
            jp.error = "Job deadline expired"
            return False

        jp.started_at = time.time()

        for attempt in range(1, self.MAX_RETRIES + 1):
            if self._stop_event.is_set():
                jp.status = JobPipelineStatus.FAILED
                jp.error = "Stopped by user"
                break

            jp.retries = attempt - 1
            jp.status = JobPipelineStatus.APPLYING
            logger.info("Applying to job %d (attempt %d/%d)", jp.job_id, attempt, self.MAX_RETRIES)

            try:
                ctx = None
                if self._browser_mgr:
                    ctx = await self._browser_mgr.launch(profile=jp.portal)

                # Run the adapter's apply flow
                result = await self._run_adapter_apply(adapter, ctx, job, profile)

                if result and result.success:
                    jp.status = JobPipelineStatus.APPLIED
                    jp.finished_at = time.time()

                    # Create application record
                    from src.core.models import ApplicationStatus
                    app_id = self._db.create_application(jp.job_id, ApplicationStatus.SUBMITTED)
                    if result.reference_id:
                        self._db.update_application_status(
                            app_id, ApplicationStatus.SUBMITTED,
                            reference_id=result.reference_id,
                        )

                    logger.info("Applied to job %d: ref=%s", jp.job_id, result.reference_id)
                    return True
                else:
                    err_msg = result.error if result else "No result returned"
                    jp.error = err_msg
                    logger.warning("Apply failed for job %d (attempt %d): %s", jp.job_id, attempt, err_msg)

            except Exception as e:
                jp.error = str(e)
                logger.error("Apply exception for job %d (attempt %d): %s", jp.job_id, attempt, e)

            # Retry delay
            if attempt < self.MAX_RETRIES:
                delay = self.RETRY_DELAY_SECONDS * attempt
                logger.info("Retrying job %d in %ds...", jp.job_id, delay)
                await asyncio.sleep(delay)

        jp.status = JobPipelineStatus.FAILED
        jp.finished_at = time.time()
        return False

    async def _run_adapter_apply(self, adapter, ctx, job, profile: dict):
        """Run the full adapter apply flow: login → search → fill → upload → submit."""
        from src.adapters.base_adapter import ApplyResult

        try:
            page = None
            if ctx:
                page = ctx.pages[0] if ctx.pages else await ctx.new_page()

            # Login
            if ctx:
                logged_in = await adapter.login(ctx)
                if not logged_in:
                    return ApplyResult(success=False, error="Login failed")

            # Navigate to job
            if page and job.url:
                await page.goto(job.url, wait_until="domcontentloaded", timeout=30000)

            # Get and fill form
            if page:
                fields = await adapter.get_application_form(page, job.url)
                filled = await adapter.fill_application(page, profile)
                if not filled:
                    return ApplyResult(success=False, error="Form fill failed")

                # Upload documents
                docs = profile.get("documents", {})
                if docs:
                    await adapter.upload_documents(page, docs)

                # Submit
                ref_id = await adapter.submit_application(page)
                return ApplyResult(success=True, reference_id=ref_id)

            return ApplyResult(success=False, error="No browser context available")

        except Exception as e:
            return ApplyResult(success=False, error=str(e))

    async def _stage_track(self, jp: JobProgress, applied: bool) -> None:
        """Stage 5: Track the application result in the database."""
        logger.debug("Stage: TRACK for job %d — applied=%s", jp.job_id, applied)
        # Application record is already created in _stage_apply_with_retries
        # This stage is for any additional tracking/logging
        if not applied and jp.status == JobPipelineStatus.FAILED:
            from src.core.models import ApplicationStatus
            existing = self._db.get_application_by_job(jp.job_id)
            if existing:
                self._db.update_application_status(
                    existing.id, ApplicationStatus.FAILED,
                    notes=jp.error,
                )

    async def _stage_learn(self) -> None:
        """Stage 6: Feed results into the learning engine."""
        logger.info("Stage: LEARNING")
        engine = self._get_learning_engine()

        for jp in self._current_run.job_progress:
            if jp.status == JobPipelineStatus.APPLIED:
                engine.track_outcome(
                    application_id=str(jp.job_id),
                    outcome="applied",
                    job_id=str(jp.job_id),
                    portal=jp.portal,
                    notes=f"Score: {jp.match_score}",
                )
            elif jp.status == JobPipelineStatus.FAILED:
                engine.track_outcome(
                    application_id=str(jp.job_id),
                    outcome="failed",
                    job_id=str(jp.job_id),
                    portal=jp.portal,
                    failure_type="apply_error",
                    reason=jp.error,
                )
            elif jp.status == JobPipelineStatus.SKIPPED:
                engine.track_outcome(
                    application_id=str(jp.job_id),
                    outcome="skipped",
                    job_id=str(jp.job_id),
                    portal=jp.portal,
                    reason=jp.error,
                )

        logger.info("Learning events tracked for %d jobs", len(self._current_run.job_progress))

    # ── Helpers ───────────────────────────────────────────────────

    def _finish(self, stage: PipelineStage) -> PipelineRun:
        """Finalize the current run."""
        self._current_run.stage = stage
        self._current_run.finished_at = datetime.now().isoformat()
        self._run_history.append(self._current_run)

        run = self._current_run
        logger.info(
            "Pipeline %s finished: stage=%s, scanned=%d, matched=%d, applied=%d, failed=%d, skipped=%d",
            run.run_id, stage.value, run.scanned, run.matched, run.applied, run.failed, run.skipped,
        )
        self._current_run = None
        return run
