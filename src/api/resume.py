"""Resume API routes — parsing, ATS scoring, keyword matching, optimization."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from src.api.app import get_config
from src.ai.brain import AIBrain
from src.ai.resume_optimizer import ResumeOptimizer, ResumeData, ResumeFormat

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class OptimizeRequest(BaseModel):
    jd_text: str
    resume_text: str
    use_ai: bool = True


class ATSScoreRequest(BaseModel):
    resume_text: str


class KeywordMatchRequest(BaseModel):
    jd_text: str
    resume_text: str


class TrackVersionRequest(BaseModel):
    application_id: str
    job_id: str
    original_path: str
    optimized_text: str
    template: str = "ats_optimized"
    keywords_added: list[str] = []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_optimizer(use_ai: bool = True) -> ResumeOptimizer:
    """Create a ResumeOptimizer, optionally wired to the AI brain."""
    brain = AIBrain(get_config()) if use_ai else None
    return ResumeOptimizer(brain=brain)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/optimize")
async def optimize_resume(req: OptimizeRequest):
    """Optimize resume text for a specific job description."""
    try:
        optimizer = _get_optimizer(use_ai=req.use_ai)
        resume_data = ResumeData(raw_text=req.resume_text)
        result = optimizer.optimize_for_job(req.jd_text, resume_data)

        return {
            "optimized_text": result.optimized_text,
            "changes": result.changes,
            "keywords_added": result.keywords_added,
            "sections_reordered": result.sections_reordered,
            "ats_score_before": result.ats_score_before,
            "ats_score_after": result.ats_score_after,
        }
    except Exception as e:
        logger.error(f"Resume optimization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ats-score")
async def ats_score(req: ATSScoreRequest):
    """Analyze ATS compatibility of resume text."""
    try:
        optimizer = _get_optimizer(use_ai=False)
        result = optimizer.analyze_ats_compatibility(req.resume_text)
        return {
            "score": result.score,
            "issues": result.issues,
            "warnings": result.warnings,
            "suggestions": result.suggestions,
            "has_tables": result.has_tables,
            "has_images": result.has_images,
            "section_detected": result.section_detected,
        }
    except Exception as e:
        logger.error(f"ATS scoring failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/match-keywords")
async def match_keywords(req: KeywordMatchRequest):
    """Match keywords between job description and resume."""
    try:
        optimizer = _get_optimizer(use_ai=False)
        result = optimizer.match_keywords(req.jd_text, req.resume_text)
        return {
            "missing": result.missing,
            "weak": result.weak,
            "strong": result.strong,
            "match_percentage": result.match_percentage,
            "total_keywords": result.total_keywords,
        }
    except Exception as e:
        logger.error(f"Keyword matching failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/parse")
async def parse_resume_file(file: UploadFile = File(...)):
    """Parse an uploaded resume file (PDF, DOCX, or TXT)."""
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in (".pdf", ".docx", ".doc", ".txt"):
        raise HTTPException(status_code=400, detail=f"Unsupported file format: {suffix}")

    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        optimizer = _get_optimizer(use_ai=False)
        result = optimizer.parse_resume(tmp_path)

        return {
            "raw_text": result.raw_text,
            "sections": result.sections,
            "skills": result.skills,
            "experience_years": result.experience_years,
            "education": result.education,
            "certifications": result.certifications,
            "file_format": result.file_format.value,
        }
    except Exception as e:
        logger.error(f"Resume parsing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@router.post("/track")
async def track_version(req: TrackVersionRequest):
    """Track a resume version for an application."""
    try:
        optimizer = _get_optimizer(use_ai=False)
        optimizer.track_resume_version(
            application_id=req.application_id,
            job_id=req.job_id,
            original_path=req.original_path,
            optimized_text=req.optimized_text,
            template=req.template,
            keywords_added=req.keywords_added,
        )
        return {"status": "tracked"}
    except Exception as e:
        logger.error(f"Resume tracking failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/versions")
async def get_versions(job_id: Optional[str] = None):
    """Get tracked resume versions, optionally filtered by job_id."""
    try:
        optimizer = _get_optimizer(use_ai=False)
        versions = optimizer.get_resume_versions(job_id)
        return {"versions": versions}
    except Exception as e:
        logger.error(f"Failed to get resume versions: {e}")
        raise HTTPException(status_code=500, detail=str(e))
