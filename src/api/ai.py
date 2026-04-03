"""AI API routes — job analysis, scoring, resume optimization."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.api.app import get_config, get_db
from src.ai.brain import AIBrain

logger = logging.getLogger(__name__)
router = APIRouter()


class MatchRequest(BaseModel):
    job: dict
    profile: dict


class OptimizeRequest(BaseModel):
    jd_text: str
    resume_text: str


class CoverLetterRequest(BaseModel):
    job: dict
    profile: dict


class ScreeningRequest(BaseModel):
    question: str
    profile: dict
    job: Optional[dict] = None


class DecideRequest(BaseModel):
    job: dict
    profile: dict
    history: Optional[list] = None


@router.post("/match")
async def analyze_match(req: MatchRequest):
    """Analyze job-profile match score."""
    brain = AIBrain(get_config())
    score = brain.analyze_job_match(req.job, req.profile)
    return {
        "score": score.score,
        "reasoning": score.reasoning,
        "skill_overlap": score.skill_overlap,
        "location_match": score.location_match,
        "salary_match": score.salary_match,
        "experience_match": score.experience_match,
        "confidence": score.confidence,
    }


@router.post("/optimize-resume")
async def optimize_resume(req: OptimizeRequest):
    """Optimize resume for a job description."""
    brain = AIBrain(get_config())
    result = brain.optimize_resume(req.jd_text, req.resume_text)
    return {
        "optimized_text": result.optimized_text,
        "changes": result.changes,
        "keywords_added": result.keywords_added,
        "sections_reordered": result.sections_reordered,
    }


@router.post("/cover-letter")
async def generate_cover_letter(req: CoverLetterRequest):
    """Generate a tailored cover letter."""
    brain = AIBrain(get_config())
    letter = brain.generate_cover_letter(req.job, req.profile)
    return {"cover_letter": letter}


@router.post("/screening")
async def answer_screening(req: ScreeningRequest):
    """Answer a screening question."""
    brain = AIBrain(get_config())
    answer = brain.answer_screening(req.question, req.profile, req.job)
    return {"answer": answer}


@router.post("/decide")
async def decide_apply(req: DecideRequest):
    """Decide whether to apply to a job."""
    brain = AIBrain(get_config())
    decision = brain.decide_apply(req.job, req.profile, req.history)
    return {"decision": decision}
