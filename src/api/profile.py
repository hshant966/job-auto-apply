"""Profile CRUD API."""
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.api.app import get_db
from src.core.models import UserProfile

router = APIRouter()


class ProfileResponse(BaseModel):
    id: int
    profile: dict
    completeness: float


@router.get("/")
async def get_profile():
    """Get the current user profile."""
    db = get_db()
    profile = db.get_profile(1)
    if not profile:
        profile = UserProfile()
        db.upsert_profile(profile, 1)
    return {
        "id": 1,
        "profile": profile.model_dump(mode="json"),
        "completeness": profile.completeness_pct(),
        "sections": profile.completeness(),
    }


@router.put("/")
async def update_profile(data: dict):
    """Update the user profile."""
    db = get_db()
    try:
        profile = UserProfile(**data)
        db.upsert_profile(profile, 1)
        return {"ok": True, "completeness": profile.completeness_pct()}
    except Exception as e:
        raise HTTPException(400, f"Invalid profile data: {e}")


@router.get("/completeness")
async def profile_completeness():
    """Get profile completeness breakdown."""
    db = get_db()
    profile = db.get_profile(1)
    if not profile:
        return {"completeness": 0, "sections": {}}
    return {
        "completeness": profile.completeness_pct(),
        "sections": profile.completeness(),
    }


@router.post("/education")
async def add_education(data: dict):
    """Add an education entry."""
    db = get_db()
    profile = db.get_profile(1) or UserProfile()
    from src.core.models import Education
    profile.education.append(Education(**data))
    db.upsert_profile(profile, 1)
    return {"ok": True, "count": len(profile.education)}


@router.post("/experience")
async def add_experience(data: dict):
    """Add a work experience entry."""
    db = get_db()
    profile = db.get_profile(1) or UserProfile()
    from src.core.models import Experience
    profile.experience.append(Experience(**data))
    db.upsert_profile(profile, 1)
    return {"ok": True, "count": len(profile.experience)}


@router.post("/skills")
async def update_skills(skills: list[str]):
    """Update skills list."""
    db = get_db()
    profile = db.get_profile(1) or UserProfile()
    profile.skills = skills
    db.upsert_profile(profile, 1)
    return {"ok": True, "skills": profile.skills}
