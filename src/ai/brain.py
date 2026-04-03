"""Central AI Engine — multi-provider support with caching and fallback."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class MatchScore:
    score: int  # 0-100
    reasoning: str = ""
    skill_overlap: float = 0.0
    location_match: bool = False
    salary_match: bool = False
    experience_match: bool = False
    confidence: float = 0.0


@dataclass
class OptimizedResume:
    original_text: str = ""
    optimized_text: str = ""
    changes: list[str] = field(default_factory=list)
    keywords_added: list[str] = field(default_factory=list)
    sections_reordered: bool = False


class RateLimiter:
    def __init__(self, rpm: int = 20, rpd: int = 200):
        self._rpm = rpm
        self._rpd = rpd
        self._minute: list[float] = []
        self._day: list[float] = []

    def acquire(self) -> bool:
        now = time.time()
        self._minute = [t for t in self._minute if now - t < 60]
        self._day = [t for t in self._day if now - t < 86400]
        if len(self._minute) >= self._rpm or len(self._day) >= self._rpd:
            return False
        self._minute.append(now)
        self._day.append(now)
        return True

    def wait_time(self) -> float:
        now = time.time()
        if self._minute:
            return max(0, 60 - (now - self._minute[0]))
        return 0.0


class AIBrain:
    """Multi-provider AI engine with caching and local fallback."""

    def __init__(self, config=None):
        from src.core.config import AppConfig
        self.config = config or AppConfig.load()
        self._limiter = RateLimiter()
        self._cache: dict[str, Any] = {}

    def _get_provider_config(self) -> tuple[str, str, str]:
        """Returns (api_base, api_key, model) for the configured provider."""
        ai = self.config.ai
        if ai.provider == "anthropic":
            return "https://api.anthropic.com/v1", ai.anthropic_api_key, ai.anthropic_model
        elif ai.provider == "openai":
            return "https://api.openai.com/v1", ai.openai_api_key, ai.openai_model
        elif ai.provider == "custom" and ai.custom_api_base:
            return ai.custom_api_base, ai.custom_api_key, ai.custom_model
        else:  # openrouter (default)
            return "https://openrouter.ai/api/v1", ai.openrouter_api_key, ai.openrouter_model

    def _call_api(self, messages: list[dict], temperature: float = 0.3) -> Optional[str]:
        """Call the configured AI API with rate limiting."""
        api_base, api_key, model = self._get_provider_config()
        if not api_key:
            logger.warning("No AI API key configured — using local fallback")
            return None

        if not self._limiter.acquire():
            wait = self._limiter.wait_time()
            logger.warning(f"Rate limited — waiting {wait:.1f}s")
            time.sleep(min(wait + 0.5, 30))
            if not self._limiter.acquire():
                return None

        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            # OpenRouter needs HTTP-Referer
            if "openrouter" in api_base:
                headers["HTTP-Referer"] = "https://github.com/job-auto-apply"

            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": 2048,
            }

            with httpx.Client(timeout=60) as client:
                resp = client.post(
                    f"{api_base}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                return content.strip() if content else None

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning("Rate limited by API, waiting 5s")
                time.sleep(5)
            else:
                logger.error(f"API error {e.response.status_code}: {e.response.text[:200]}")
            return None
        except Exception as e:
            logger.error(f"API call failed: {e}")
            return None

    def analyze_job_match(self, job: dict, profile: dict) -> MatchScore:
        """Analyze how well a job matches a profile."""
        # Check in-memory cache
        cache_key = f"match:{hashlib.md5(json.dumps(job, sort_keys=True, default=str)[:500].encode()).hexdigest()}"
        if cache_key in self._cache:
            return MatchScore(**self._cache[cache_key])

        prompt = (
            "Analyze how well this job matches the candidate profile. "
            "Return JSON with: score (0-100), reasoning, skill_overlap (0.0-1.0), "
            "location_match (bool), salary_match (bool), experience_match (bool), confidence (0.0-1.0).\n\n"
            f"JOB:\n{json.dumps(job, indent=2, default=str)[:3000]}\n\n"
            f"PROFILE:\n{json.dumps(profile, indent=2, default=str)[:3000]}\n\n"
            "Respond with ONLY the JSON object."
        )

        response = self._call_api([
            {"role": "system", "content": "You are a job matching expert. Respond only with valid JSON."},
            {"role": "user", "content": prompt},
        ])

        if response:
            try:
                text = response.strip()
                if text.startswith("```"):
                    text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
                result = json.loads(text)
                score = MatchScore(
                    score=max(0, min(100, int(result.get("score", 0)))),
                    reasoning=result.get("reasoning", ""),
                    skill_overlap=float(result.get("skill_overlap", 0)),
                    location_match=bool(result.get("location_match", False)),
                    salary_match=bool(result.get("salary_match", False)),
                    experience_match=bool(result.get("experience_match", False)),
                    confidence=float(result.get("confidence", 0.5)),
                )
                self._cache[cache_key] = {"score": score.score, "reasoning": score.reasoning,
                    "skill_overlap": score.skill_overlap, "location_match": score.location_match,
                    "salary_match": score.salary_match, "experience_match": score.experience_match,
                    "confidence": score.confidence}
                return score
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.warning(f"Failed to parse AI response: {e}")

        return self._local_match(job, profile)

    def _local_match(self, job: dict, profile: dict) -> MatchScore:
        """Keyword-based local matching fallback."""
        job_text = f"{job.get('title', '')} {job.get('description', '')}".lower()
        user_skills = [s.lower() for s in profile.get("skills", [])]
        if not user_skills:
            return MatchScore(score=10, reasoning="No skills in profile", confidence=0.3)

        matched = [s for s in user_skills if s in job_text]
        skill_overlap = len(matched) / len(user_skills)

        job_loc = job.get("location", "").lower()
        pref_locs = [l.lower() for l in profile.get("preferred_locations", profile.get("locations", []))]
        loc_match = any(loc in job_loc for loc in pref_locs) if pref_locs else True

        score = int(skill_overlap * 60 + (25 if loc_match else 0) + 15)
        return MatchScore(
            score=min(100, score),
            reasoning=f"Local: {len(matched)}/{len(user_skills)} skills matched",
            skill_overlap=skill_overlap,
            location_match=loc_match,
            confidence=0.4,
        )

    def generate_cover_letter(self, job: dict, profile: dict) -> str:
        """Generate a tailored cover letter."""
        prompt = (
            "Write a professional cover letter (under 300 words) for this job. "
            "Be specific about matching skills.\n\n"
            f"JOB:\n{json.dumps(job, indent=2, default=str)[:2000]}\n\n"
            f"CANDIDATE:\n{json.dumps(profile, indent=2, default=str)[:2000]}\n\n"
            "Write the cover letter only."
        )
        response = self._call_api([
            {"role": "system", "content": "You write concise professional cover letters."},
            {"role": "user", "content": prompt},
        ])
        if response:
            return response
        name = profile.get("full_name", profile.get("name", "Applicant"))
        skills = ", ".join(profile.get("skills", [])[:5])
        return (
            f"Dear Hiring Manager,\n\n"
            f"I am writing to express interest in the {job.get('title', 'position')} role. "
            f"With my background in {skills}, I believe I would be a strong fit.\n\n"
            f"Best regards,\n{name}"
        )

    def optimize_resume(self, jd_text: str, resume_text: str) -> OptimizedResume:
        """Optimize resume for a specific job description."""
        prompt = (
            "Optimize this resume for the job description. Return JSON with: "
            "optimized_text, changes (list), keywords_added (list), sections_reordered (bool).\n\n"
            f"JOB:\n{jd_text[:4000]}\n\nRESUME:\n{resume_text[:4000]}\n\n"
            "Respond with ONLY valid JSON."
        )
        response = self._call_api([
            {"role": "system", "content": "You optimize resumes for ATS. Respond only with JSON."},
            {"role": "user", "content": prompt},
        ])
        if response:
            try:
                text = response.strip()
                if text.startswith("```"):
                    text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
                result = json.loads(text)
                return OptimizedResume(
                    original_text=resume_text,
                    optimized_text=result.get("optimized_text", resume_text),
                    changes=result.get("changes", []),
                    keywords_added=result.get("keywords_added", []),
                    sections_reordered=result.get("sections_reordered", False),
                )
            except (json.JSONDecodeError, KeyError):
                pass
        return OptimizedResume(original_text=resume_text, optimized_text=resume_text,
                               changes=["API unavailable"])

    def answer_screening(self, question: str, profile: dict, job: Optional[dict] = None) -> str:
        """Answer a screening question."""
        ctx = json.dumps(job, indent=2, default=str)[:1000] if job else "N/A"
        prompt = (
            f"Answer this screening question concisely (under 2 sentences).\n\n"
            f"Q: {question}\n\nPROFILE:\n{json.dumps(profile, indent=2, default=str)[:2000]}\n\n"
            f"JOB CONTEXT: {ctx}\n\nAnswer:"
        )
        response = self._call_api([
            {"role": "system", "content": "Answer screening questions concisely and professionally."},
            {"role": "user", "content": prompt},
        ], temperature=0.2)
        if response:
            return response
        # Fallback
        q = question.lower()
        if "year" in q and "experience" in q:
            return str(profile.get("years_of_experience", "Not specified"))
        if "salary" in q or "ctc" in q:
            return str(profile.get("expected_salary", "Negotiable"))
        if "notice" in q:
            return str(profile.get("notice_period", "Immediate"))
        return "Please refer to my resume for details."

    def decide_apply(self, job: dict, profile: dict, history: Optional[list] = None) -> str:
        """Decide: 'apply', 'skip', or 'defer'."""
        score = self.analyze_job_match(job, profile)
        min_score = profile.get("min_match_score", self.config.scan.min_match_score)
        if score.score < min_score:
            return "skip"
        if history:
            for h in history:
                if h.get("title", "").lower() == job.get("title", "").lower():
                    return "skip"
        if score.score >= min_score + 20:
            return "apply"
        if score.confidence > 0.6:
            return "apply"
        return "defer"
