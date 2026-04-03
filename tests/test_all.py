"""JobAutoApply — Test Suite."""

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.database import Database
from src.core.models import (
    UserProfile, PersonalInfo, ContactInfo, Address, Education,
    Job, Application, ApplicationStatus, Gender,
)


@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    db = Database(db_path)
    yield db
    db.close()
    os.unlink(db_path)


@pytest.fixture
def sample_profile():
    return UserProfile(
        personal=PersonalInfo(full_name="Test User", dob="1995-06-15", gender=Gender.MALE),
        contact=ContactInfo(email="test@example.com", phone="9876543210", address=Address(city="Delhi", state="Delhi")),
        education=[Education(degree="B.Tech", university="Delhi University", year_of_passing=2017, percentage=85.0)],
        skills=["python", "java", "sql", "react"],
    )


@pytest.fixture
def sample_job():
    return Job(title="Senior Python Developer", portal="linkedin", url="https://linkedin.com/jobs/12345", department="Engineering", location="Delhi", salary="15-25 LPA", match_score=85)


# ═══════════════ Database Tests ═══════════════

class TestDatabase:
    def test_create_profile(self, temp_db, sample_profile):
        pid = temp_db.create_profile(sample_profile)
        assert pid > 0
        assert temp_db.get_profile(pid).personal.full_name == "Test User"

    def test_update_profile(self, temp_db, sample_profile):
        pid = temp_db.create_profile(sample_profile)
        sample_profile.personal.full_name = "Updated"
        temp_db.update_profile(pid, sample_profile)
        assert temp_db.get_profile(pid).personal.full_name == "Updated"

    def test_upsert_profile(self, temp_db, sample_profile):
        pid = temp_db.upsert_profile(sample_profile)
        assert pid > 0
        sample_profile.personal.full_name = "Upserted"
        temp_db.upsert_profile(sample_profile, profile_id=pid)
        assert temp_db.get_profile(pid).personal.full_name == "Upserted"

    def test_save_job(self, temp_db, sample_job):
        jid = temp_db.save_job(sample_job)
        assert jid > 0
        assert temp_db.get_job(jid).title == "Senior Python Developer"

    def test_search_jobs(self, temp_db, sample_job):
        temp_db.save_job(sample_job)
        assert len(temp_db.search_jobs(portal="linkedin")) == 1
        assert len(temp_db.search_jobs(portal="naukri")) == 0

    def test_count_jobs(self, temp_db, sample_job):
        assert temp_db.count_jobs() == 0
        temp_db.save_job(sample_job)
        assert temp_db.count_jobs() == 1

    def test_application_lifecycle(self, temp_db, sample_job):
        jid = temp_db.save_job(sample_job)
        aid = temp_db.create_application(jid, ApplicationStatus.DRAFT)
        temp_db.update_application_status(aid, ApplicationStatus.SUBMITTED, reference_id="REF123")
        app = temp_db.get_application(aid)
        assert app.status == ApplicationStatus.SUBMITTED
        assert app.reference_id == "REF123"

    def test_application_stats(self, temp_db, sample_job):
        jid = temp_db.save_job(sample_job)
        temp_db.create_application(jid, ApplicationStatus.SUBMITTED)
        temp_db.create_application(jid, ApplicationStatus.DRAFT)
        stats = temp_db.application_stats()
        assert stats["total_applications"] == 2
        assert stats["submitted"] == 1

    def test_settings(self, temp_db):
        temp_db.set_setting("key", "value")
        assert temp_db.get_setting("key") == "value"
        assert temp_db.get_setting("missing", "default") == "default"

    def test_portal_sessions(self, temp_db):
        cookies = [{"name": "session", "value": "abc"}]
        temp_db.save_portal_session("linkedin", cookies, {"logged_in": True})
        session = temp_db.get_portal_session("linkedin")
        assert session["cookies"] == cookies

    def test_ai_cache(self, temp_db):
        temp_db.cache_set("k", {"score": 85})
        assert temp_db.cache_get("k")["score"] == 85

    def test_upcoming_deadlines(self, temp_db):
        from datetime import date, timedelta
        j = Job(title="Urgent", portal="test", url="https://test.com/1", last_date=date.today() + timedelta(days=3))
        temp_db.save_job(j)
        assert len(temp_db.upcoming_deadlines(days=7)) >= 1


# ═══════════════ Model Tests ═══════════════

class TestModels:
    def test_profile_completeness(self, sample_profile):
        assert sample_profile.completeness_pct() > 50

    def test_empty_profile(self):
        assert UserProfile().completeness_pct() == 0.0

    def test_job_expiry(self):
        from datetime import date, timedelta
        assert Job(title="X").is_expired is False
        assert Job(title="X", last_date=date.today() - timedelta(days=1)).is_expired is True

    def test_aadhaar_validation(self):
        assert PersonalInfo(aadhaar_last4="1234").aadhaar_last4 == "1234"
        with pytest.raises(ValueError):
            PersonalInfo(aadhaar_last4="12345")


# ═══════════════ AI Brain Tests ═══════════════

class TestAIBrain:
    def test_local_match(self):
        from src.ai.brain import AIBrain
        brain = AIBrain()
        job = {"title": "Python Developer", "description": "Python SQL Django", "location": "Delhi"}
        profile = {"skills": ["python", "java", "sql"], "preferred_locations": ["Delhi"]}
        score = brain.analyze_job_match(job, profile)
        assert score.score > 0
        assert score.skill_overlap > 0
        assert score.location_match is True

    def test_no_skills(self):
        from src.ai.brain import AIBrain
        score = AIBrain().analyze_job_match({"title": "Dev"}, {"skills": []})
        assert score.score <= 20

    def test_decide(self):
        from src.ai.brain import AIBrain
        job = {"title": "Python Dev", "description": "Python SQL", "location": "Delhi"}
        profile = {"skills": ["python"], "preferred_locations": ["Delhi"], "min_match_score": 30}
        assert AIBrain().decide_apply(job, profile) in ("apply", "skip", "defer")

    def test_cover_letter(self):
        from src.ai.brain import AIBrain
        letter = AIBrain().generate_cover_letter({"title": "SE"}, {"full_name": "Test", "skills": ["python"]})
        assert "Test" in letter

    def test_screening(self):
        from src.ai.brain import AIBrain
        assert "5" in AIBrain().answer_screening("years of experience?", {"years_of_experience": 5})


# ═══════════════ Stealth Tests ═══════════════

class TestStealth:
    def test_random_ua(self):
        from src.browser.stealth import StealthManager
        assert "Mozilla" in StealthManager.random_ua()

    def test_random_viewport(self):
        from src.browser.stealth import StealthManager
        vp = StealthManager.random_viewport()
        assert vp[0] > 1000 and vp[1] > 600


# ═══════════════ Config Tests ═══════════════

class TestConfig:
    def test_default_config(self):
        from src.core.config import AppConfig
        cfg = AppConfig()
        assert cfg.db_path == "data/jobs.db"
        assert cfg.ai.provider == "openrouter"

    def test_config_load(self):
        from src.core.config import AppConfig
        cfg = AppConfig.load()
        assert cfg.scan.interval_minutes > 0


# ═══════════════ Adapter Tests ═══════════════

class TestAdapters:
    def test_registry(self):
        from src.adapters import ADAPTER_REGISTRY
        assert "ssc" in ADAPTER_REGISTRY
        assert "upsc" in ADAPTER_REGISTRY
        assert "linkedin" in ADAPTER_REGISTRY
        assert "naukri" in ADAPTER_REGISTRY
        assert "indeed" in ADAPTER_REGISTRY
        assert "rrb" in ADAPTER_REGISTRY
        assert "ibps" in ADAPTER_REGISTRY
        assert len(ADAPTER_REGISTRY) == 7


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
