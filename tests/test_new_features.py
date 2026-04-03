"""Tests for new feature modules — imports, API routes, and module-level contracts."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ═══════════════════════════════════════════════════════════════════════════════
# Module Import Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestRadarScannerImports:
    """Test that radar_scanner module imports cleanly."""

    def test_module_imports(self):
        from src.ai import radar_scanner
        assert hasattr(radar_scanner, "RadarScanner")
        assert hasattr(radar_scanner, "ScanResult")
        assert hasattr(radar_scanner, "DEFAULT_RSS_FEEDS")

    def test_scan_result_dataclass(self):
        from src.ai.radar_scanner import ScanResult
        result = ScanResult()
        assert result.new_jobs == []
        assert result.total_found == 0
        assert result.duplicates_removed == 0
        assert result.sources_scanned == 0
        assert result.errors == []
        assert result.scan_duration_seconds == 0.0

    def test_default_rss_feeds(self):
        from src.ai.radar_scanner import DEFAULT_RSS_FEEDS
        assert isinstance(DEFAULT_RSS_FEEDS, dict)
        assert len(DEFAULT_RSS_FEEDS) >= 1
        for name, url in DEFAULT_RSS_FEEDS.items():
            assert url.startswith("http")

    def test_radar_scanner_init(self):
        from src.ai.radar_scanner import RadarScanner
        mock_db = MagicMock()
        scanner = RadarScanner(db=mock_db)
        assert scanner.sources is not None
        assert len(scanner.sources) >= 1

    def test_radar_scanner_custom_feeds(self):
        from src.ai.radar_scanner import RadarScanner
        mock_db = MagicMock()
        feeds = {"custom": "https://example.com/rss"}
        scanner = RadarScanner(db=mock_db, rss_feeds=feeds)
        assert scanner.sources == feeds

    def test_radar_scanner_scan_interval(self):
        from src.ai.radar_scanner import RadarScanner
        mock_db = MagicMock()
        scanner = RadarScanner(db=mock_db)
        assert scanner.scan_interval_hours > 0

    def test_radar_scanner_scan_all_sources_callable(self):
        from src.ai.radar_scanner import RadarScanner
        mock_db = MagicMock()
        scanner = RadarScanner(db=mock_db, rss_feeds={})  # No feeds → no actual requests
        assert callable(scanner.scan_all_sources)


class TestSelfLearningImports:
    """Test that self_learning module imports cleanly."""

    def test_module_imports(self):
        from src.ai import self_learning
        assert hasattr(self_learning, "SelfLearningEngine")
        assert hasattr(self_learning, "Outcome")
        assert hasattr(self_learning, "FailureAnalysis")
        assert hasattr(self_learning, "StrategyUpdate")
        assert hasattr(self_learning, "LearningReport")

    def test_outcome_constants(self):
        from src.ai.self_learning import Outcome
        assert Outcome.PENDING == "pending"
        assert Outcome.APPLIED == "applied"
        assert Outcome.REJECTED == "rejected"
        assert Outcome.FAILED == "failed"
        assert Outcome.OFFERED == "offered"
        assert Outcome.INTERVIEW == "interview"

    def test_failure_analysis_defaults(self):
        from src.ai.self_learning import FailureAnalysis
        fa = FailureAnalysis()
        assert fa.total_applications == 0
        assert fa.failure_rate == 0.0
        assert fa.failures_by_portal == {}

    def test_strategy_update_defaults(self):
        from src.ai.self_learning import StrategyUpdate
        su = StrategyUpdate()
        assert su.credential_rotation is False
        assert su.proxy_rotation is False
        assert su.max_retries_adjusted is None

    def test_learning_report_defaults(self):
        from src.ai.self_learning import LearningReport
        lr = LearningReport()
        assert lr.total_applications == 0
        assert lr.success_rate == 0.0

    def test_self_learning_engine_track_outcome(self):
        from src.ai.self_learning import SelfLearningEngine
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_db.get_conn.return_value = mock_conn

        engine = SelfLearningEngine(db=mock_db)
        engine.track_outcome("app1", "applied", portal="linkedin")
        mock_conn.execute.assert_called()
        mock_conn.commit.assert_called()


class TestResumeOptimizerImports:
    """Test that resume_optimizer module imports cleanly."""

    def test_module_imports(self):
        from src.ai import resume_optimizer
        assert hasattr(resume_optimizer, "ResumeOptimizer")
        assert hasattr(resume_optimizer, "ResumeData")
        assert hasattr(resume_optimizer, "ATSScore")
        assert hasattr(resume_optimizer, "KeywordMatch")
        assert hasattr(resume_optimizer, "OptimizedResume")

    def test_resume_format_enum(self):
        from src.ai.resume_optimizer import ResumeFormat
        assert ResumeFormat.PDF.value == "pdf"
        assert ResumeFormat.DOCX.value == "docx"
        assert ResumeFormat.TXT.value == "txt"

    def test_resume_data_defaults(self):
        from src.ai.resume_optimizer import ResumeData
        rd = ResumeData(raw_text="test")
        assert rd.raw_text == "test"
        assert rd.sections == {}
        assert rd.skills == []
        assert rd.experience_years is None

    def test_ats_score_defaults(self):
        from src.ai.resume_optimizer import ATSScore
        score = ATSScore(score=85)
        assert score.score == 85
        assert score.issues == []
        assert score.has_tables is False

    def test_keyword_match_defaults(self):
        from src.ai.resume_optimizer import KeywordMatch
        km = KeywordMatch()
        assert km.missing == []
        assert km.strong == []
        assert km.match_percentage == 0.0

    def test_optimized_resume_defaults(self):
        from src.ai.resume_optimizer import OptimizedResume
        or_ = OptimizedResume(original_text="x", optimized_text="x")
        assert or_.changes == []
        assert or_.keywords_added == []

    def test_resume_optimizer_init(self, tmp_path):
        from src.ai.resume_optimizer import ResumeOptimizer
        db_path = str(tmp_path / "test_resumes.db")
        optimizer = ResumeOptimizer(db_path=db_path)
        assert callable(optimizer.parse_resume)
        assert callable(optimizer.analyze_ats_compatibility)
        assert callable(optimizer.match_keywords)
        assert callable(optimizer.optimize_for_job)
        assert callable(optimizer.generate_formatted_resume)
        assert callable(optimizer.track_resume_version)

    def test_ats_compatibility_analyzer(self, tmp_path):
        from src.ai.resume_optimizer import ResumeOptimizer
        db_path = str(tmp_path / "test_resumes.db")
        optimizer = ResumeOptimizer(db_path=db_path)

        good_resume = """
        John Doe
        john@example.com | +91 9876543210

        SKILLS
        Python, Java, SQL, AWS, Docker

        EXPERIENCE
        Software Engineer at Acme Corp (2018-2023)
        5 years of experience in software development.

        EDUCATION
        B.Tech Computer Science, Delhi University, 2017
        """
        score = optimizer.analyze_ats_compatibility(good_resume)
        assert score.score > 50
        assert not score.has_tables

    def test_ats_compatibility_detects_tables(self, tmp_path):
        from src.ai.resume_optimizer import ResumeOptimizer
        db_path = str(tmp_path / "test_resumes.db")
        optimizer = ResumeOptimizer(db_path=db_path)

        bad_resume = "<table><tr><td>Name</td><td>John</td></tr></table>"
        score = optimizer.analyze_ats_compatibility(bad_resume)
        assert score.has_tables is True
        assert len(score.issues) > 0

    def test_keyword_matcher(self, tmp_path):
        from src.ai.resume_optimizer import ResumeOptimizer
        db_path = str(tmp_path / "test_resumes.db")
        optimizer = ResumeOptimizer(db_path=db_path)

        jd = "We need a Python developer with SQL and AWS experience."
        resume = "Experienced Python developer. Skills: Python, SQL, Docker."
        match = optimizer.match_keywords(jd, resume)
        # Keywords are extracted lowercase from JD
        assert "python" in [s.lower() for s in match.strong]
        assert "aws" in [m.lower() for m in match.missing]
        assert match.total_keywords > 0

    def test_local_optimization(self, tmp_path):
        from src.ai.resume_optimizer import ResumeOptimizer, ResumeData
        db_path = str(tmp_path / "test_resumes.db")
        optimizer = ResumeOptimizer(db_path=db_path)

        resume = ResumeData(raw_text="Software Engineer. Skills: Python, Java. 3 years experience.")
        result = optimizer.optimize_for_job(
            "Looking for Python developer with AWS and Kubernetes skills.",
            resume,
        )
        assert isinstance(result.optimized_text, str)
        assert isinstance(result.changes, list)

    def test_generate_formatted_resume(self, tmp_path):
        from src.ai.resume_optimizer import ResumeOptimizer, OptimizedResume
        db_path = str(tmp_path / "test_resumes.db")
        optimizer = ResumeOptimizer(db_path=db_path)

        optimized = OptimizedResume(original_text="test", optimized_text="test resume")
        for template in ("ats_optimized", "govt_format", "private_format"):
            result = optimizer.generate_formatted_resume(optimized, template=template)
            assert isinstance(result, bytes)

    def test_resume_version_tracking(self, tmp_path):
        from src.ai.resume_optimizer import ResumeOptimizer
        db_path = str(tmp_path / "test_resumes.db")
        optimizer = ResumeOptimizer(db_path=db_path)

        optimizer.track_resume_version(
            application_id="app1",
            job_id="job1",
            original_path="/tmp/resume.txt",
            optimized_text="optimized text",
            template="ats_optimized",
            keywords_added=["AWS"],
        )
        versions = optimizer.get_resume_versions(job_id="job1")
        assert len(versions) == 1
        assert versions[0]["application_id"] == "app1"


class TestSessionPersistenceImports:
    """Test that session_persistence module imports cleanly."""

    def test_module_imports(self):
        from src.browser import session_persistence
        assert hasattr(session_persistence, "SessionPersistence")
        assert hasattr(session_persistence, "SESSION_EXPIRY_DAYS")

    def test_session_expiry_constant(self):
        from src.browser.session_persistence import SESSION_EXPIRY_DAYS
        assert SESSION_EXPIRY_DAYS == 30

    def test_init(self):
        from src.browser.session_persistence import SessionPersistence
        mock_db = MagicMock()
        sp = SessionPersistence(db=mock_db)
        assert sp._db is mock_db

    def test_methods_exist(self):
        from src.browser.session_persistence import SessionPersistence
        mock_db = MagicMock()
        sp = SessionPersistence(db=mock_db)
        assert callable(sp.save_session)
        assert callable(sp.restore_session)
        assert callable(sp.save_cookies)
        assert callable(sp.load_cookies)
        assert callable(sp.delete_session)
        assert callable(sp.list_sessions)
        assert callable(sp.cleanup_expired)

    def test_delete_session_returns_false_when_empty(self):
        from src.browser.session_persistence import SessionPersistence
        mock_db = MagicMock()
        mock_db.get_portal_session.return_value = {}
        sp = SessionPersistence(db=mock_db)
        assert sp.delete_session("linkedin") is False

    def test_list_sessions(self):
        from src.browser.session_persistence import SessionPersistence
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_db.get_conn.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = [
            {"portal": "linkedin", "updated_at": 1234567890},
        ]
        mock_db.get_portal_session.return_value = {"cookies": [{"name": "sid"}]}
        mock_db.get_setting.return_value = None

        sp = SessionPersistence(db=mock_db)
        sessions = sp.list_sessions()
        assert len(sessions) == 1
        assert sessions[0]["portal"] == "linkedin"
        assert sessions[0]["cookie_count"] == 1


class TestNavigationHelperImports:
    """Test that navigation_helper module imports cleanly."""

    def test_module_imports(self):
        from src.browser import navigation_helper
        assert hasattr(navigation_helper, "NavigationHelper")

    def test_init_defaults(self):
        from src.browser.navigation_helper import NavigationHelper
        nh = NavigationHelper()
        assert nh._default_timeout == 30_000
        assert nh._max_retries == 3

    def test_init_custom(self):
        from src.browser.navigation_helper import NavigationHelper
        nh = NavigationHelper(default_timeout=10000, max_retries=5)
        assert nh._default_timeout == 10000
        assert nh._max_retries == 5

    def test_popup_selectors_not_empty(self):
        from src.browser.navigation_helper import NavigationHelper
        assert len(NavigationHelper.POPUP_SELECTORS) > 10

    def test_methods_exist(self):
        from src.browser.navigation_helper import NavigationHelper
        nh = NavigationHelper()
        assert callable(nh.safe_goto)
        assert callable(nh.retry_navigation)
        assert callable(nh.wait_and_click)
        assert callable(nh.smart_wait)
        assert callable(nh.handle_popups)
        assert callable(nh.handle_redirect)
        assert callable(nh.wait_for_page_ready)
        assert callable(nh.scroll_to_bottom)


# ═══════════════════════════════════════════════════════════════════════════════
# API Route Registration Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestAPIRouteRegistration:
    """Test that new API routes are registered in the app."""

    @pytest.fixture
    def app(self):
        from src.api.app import create_app
        return create_app()

    def _get_route_paths(self, app):
        """Extract all registered route paths."""
        paths = set()
        for route in app.routes:
            if hasattr(route, "path"):
                paths.add(route.path)
            if hasattr(route, "routes"):
                # Include sub-routes from routers
                for sub_route in route.routes:
                    if hasattr(sub_route, "path"):
                        paths.add(sub_route.path)
        return paths

    def _get_route_path_patterns(self, app):
        """Extract route path patterns (including params)."""
        patterns = set()
        for route in app.routes:
            if hasattr(route, "path"):
                patterns.add(route.path)
            if hasattr(route, "path_regex"):
                patterns.add(route.path)
            # Routers
            if hasattr(route, "routes"):
                for sub in route.routes:
                    if hasattr(sub, "path"):
                        patterns.add(sub.path)
        return patterns

    def test_radar_routes_registered(self, app):
        paths = self._get_route_paths(app)
        radar_paths = [p for p in paths if "/api/radar" in p]
        assert len(radar_paths) >= 2, (
            f"Expected at least 2 /api/radar routes, found: {radar_paths}"
        )

    def test_learning_routes_registered(self, app):
        paths = self._get_route_paths(app)
        learning_paths = [p for p in paths if "/api/learning" in p]
        assert len(learning_paths) >= 3, (
            f"Expected at least 3 /api/learning routes, found: {learning_paths}"
        )

    def test_resume_routes_registered(self, app):
        paths = self._get_route_paths(app)
        resume_paths = [p for p in paths if "/api/resume" in p]
        assert len(resume_paths) >= 3, (
            f"Expected at least 3 /api/resume routes, found: {resume_paths}"
        )

    def test_radar_has_scan_endpoint(self, app):
        paths = self._get_route_paths(app)
        assert any("/scan" in p for p in paths if "/api/radar" in p), (
            "Missing /api/radar/scan endpoint"
        )

    def test_radar_has_sources_endpoint(self, app):
        paths = self._get_route_paths(app)
        assert any("/sources" in p for p in paths if "/api/radar" in p), (
            "Missing /api/radar/sources endpoint"
        )

    def test_learning_has_analyze_endpoint(self, app):
        paths = self._get_route_paths(app)
        assert any("/analyze" in p for p in paths if "/api/learning" in p), (
            "Missing /api/learning/analyze endpoint"
        )

    def test_learning_has_insights_endpoint(self, app):
        paths = self._get_route_paths(app)
        assert any("/insights" in p for p in paths if "/api/learning" in p), (
            "Missing /api/learning/insights endpoint"
        )

    def test_learning_has_track_endpoint(self, app):
        paths = self._get_route_paths(app)
        assert any("/track" in p for p in paths if "/api/learning" in p), (
            "Missing /api/learning/track endpoint"
        )

    def test_resume_has_optimize_endpoint(self, app):
        paths = self._get_route_paths(app)
        assert any("/optimize" in p for p in paths if "/api/resume" in p), (
            "Missing /api/resume/optimize endpoint"
        )

    def test_resume_has_ats_score_endpoint(self, app):
        paths = self._get_route_paths(app)
        assert any("/ats-score" in p for p in paths if "/api/resume" in p), (
            "Missing /api/resume/ats-score endpoint"
        )

    def test_resume_has_match_keywords_endpoint(self, app):
        paths = self._get_route_paths(app)
        assert any("/match-keywords" in p for p in paths if "/api/resume" in p), (
            "Missing /api/resume/match-keywords endpoint"
        )

    def test_all_expected_route_prefixes(self, app):
        """Verify all major route prefixes are registered."""
        paths = self._get_route_paths(app)
        all_paths_str = " ".join(paths)
        for prefix in ["/api/auth", "/api/profile", "/api/jobs", "/api/apply",
                       "/api/browser", "/api/ai", "/api/dashboard", "/api/portals",
                       "/api/settings", "/api/resume", "/api/learning", "/api/radar"]:
            assert prefix in all_paths_str, f"Missing route prefix: {prefix}"
