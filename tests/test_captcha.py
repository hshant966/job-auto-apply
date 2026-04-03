"""Tests for CAPTCHA handler module — CaptchaHandler, CaptchaInfo, strategies, stats."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ═══════════════════════════════════════════════════════════════════════════════
# Data types
# ═══════════════════════════════════════════════════════════════════════════════

from src.browser.captcha_handler import (
    CaptchaType,
    SolveStrategy,
    CaptchaInfo,
    SolveResult,
    CaptchaHandler,
    CAPTCHA_SELECTORS,
    OcrStrategy,
    PaidServiceStrategy,
    ManualStrategy,
)


class TestCaptchaType:
    """Test CaptchaType enum."""

    def test_all_types_exist(self):
        expected = {
            "text_image", "recaptcha_v2", "recaptcha_v3",
            "hcaptcha", "slider", "image_select", "math", "unknown",
        }
        actual = {t.value for t in CaptchaType}
        assert expected == actual

    def test_is_string_enum(self):
        assert CaptchaType.TEXT_IMAGE == "text_image"
        assert CaptchaType.TEXT_IMAGE.value == "text_image"

    def test_from_string(self):
        assert CaptchaType("recaptcha_v2") == CaptchaType.RECAPTCHA_V2


class TestSolveStrategy:
    """Test SolveStrategy enum."""

    def test_all_strategies_exist(self):
        expected = {"ocr", "ai", "paid_service", "manual"}
        actual = {s.value for s in SolveStrategy}
        assert expected == actual


class TestCaptchaInfo:
    """Test CaptchaInfo dataclass."""

    def test_default_values(self):
        info = CaptchaInfo()
        assert info.found is False
        assert info.captcha_type == CaptchaType.UNKNOWN
        assert info.selector == ""
        assert info.img_selector == ""
        assert info.input_selector == ""
        assert info.sitekey == ""
        assert info.page_url == ""
        assert info.extra == {}

    def test_custom_values(self):
        info = CaptchaInfo(
            found=True,
            captcha_type=CaptchaType.RECAPTCHA_V2,
            selector="iframe[src*='recaptcha']",
            sitekey="abc123",
            page_url="https://example.com",
            extra={"foo": "bar"},
        )
        assert info.found is True
        assert info.captcha_type == CaptchaType.RECAPTCHA_V2
        assert info.sitekey == "abc123"
        assert info.extra == {"foo": "bar"}


class TestSolveResult:
    """Test SolveResult dataclass."""

    def test_default_values(self):
        result = SolveResult()
        assert result.success is False
        assert result.answer == ""
        assert result.strategy_used == SolveStrategy.OCR
        assert result.confidence == 0.0
        assert result.cost == 0.0
        assert result.attempts == 0
        assert result.error == ""
        assert result.elapsed_ms == 0

    def test_custom_values(self):
        result = SolveResult(
            success=True,
            answer="ABC123",
            strategy_used=SolveStrategy.AI,
            confidence=0.85,
            cost=0.003,
            elapsed_ms=1500,
        )
        assert result.success is True
        assert result.answer == "ABC123"
        assert result.confidence == 0.85


# ═══════════════════════════════════════════════════════════════════════════════
# Selectors
# ═══════════════════════════════════════════════════════════════════════════════

class TestCaptchaSelectors:
    """Test CAPTCHA_SELECTORS dictionary."""

    def test_all_types_have_selectors(self):
        for ctype in CaptchaType:
            if ctype == CaptchaType.UNKNOWN:
                continue  # UNKNOWN has no selectors
            assert ctype in CAPTCHA_SELECTORS, f"Missing selectors for {ctype}"

    def test_text_image_has_container_and_input(self):
        sel = CAPTCHA_SELECTORS[CaptchaType.TEXT_IMAGE]
        assert "container" in sel
        assert "input" in sel
        assert "captcha" in sel["container"].lower()

    def test_recaptcha_v2_has_container(self):
        sel = CAPTCHA_SELECTORS[CaptchaType.RECAPTCHA_V2]
        assert "recaptcha" in sel["container"]


# ═══════════════════════════════════════════════════════════════════════════════
# CaptchaHandler
# ═══════════════════════════════════════════════════════════════════════════════

class TestCaptchaHandler:
    """Test CaptchaHandler initialization and configuration."""

    @pytest.fixture
    def mock_config(self):
        cfg = MagicMock()
        cfg.browser.screenshot_dir = "/tmp/screenshots"
        return cfg

    @pytest.fixture
    def handler(self, mock_config):
        return CaptchaHandler(config=mock_config)

    def test_init_default_strategy_order(self, handler):
        assert handler.strategy_order == [
            SolveStrategy.OCR,
            SolveStrategy.AI,
            SolveStrategy.PAID_SERVICE,
            SolveStrategy.MANUAL,
        ]

    def test_set_strategy_order(self, handler):
        new_order = [SolveStrategy.AI, SolveStrategy.OCR]
        handler.set_strategy_order(new_order)
        assert handler.strategy_order == new_order

    def test_configure_paid_service(self, handler):
        handler.configure_paid_service(service="2captcha", api_key="fake_key")
        assert handler._paid_service is not None
        assert handler._paid_service.service == "2captcha"

    def test_configure_paid_service_empty_key(self, handler):
        handler.configure_paid_service(api_key="")
        assert handler._paid_service is None

    def test_total_cost_no_paid_service(self, handler):
        assert handler.total_cost == 0.0

    def test_total_cost_with_paid_service(self, handler):
        handler.configure_paid_service(service="2captcha", api_key="fake")
        handler._paid_service._cost_tracker = [0.003, 0.003]
        assert handler.total_cost == 0.006

    def test_solve_history_empty(self, handler):
        assert handler.solve_history == []

    def test_get_stats_empty(self, handler):
        stats = handler.get_stats()
        assert stats["total_attempts"] == 0
        assert stats["solved"] == 0
        assert stats["failed"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["total_cost_usd"] == 0.0
        assert stats["by_strategy"] == {}

    def test_get_stats_with_history(self, handler):
        handler._solve_history = [
            SolveResult(success=True, strategy_used=SolveStrategy.OCR),
            SolveResult(success=False, strategy_used=SolveStrategy.AI, error="fail"),
            SolveResult(success=True, strategy_used=SolveStrategy.OCR),
        ]
        stats = handler.get_stats()
        assert stats["total_attempts"] == 3
        assert stats["solved"] == 2
        assert stats["failed"] == 1
        assert abs(stats["success_rate"] - 2 / 3) < 0.01
        assert stats["by_strategy"]["ocr"] == 2
        assert stats["by_strategy"]["ai"] == 1


class TestCaptchaHandlerDetect:
    """Test CaptchaHandler.detect()."""

    @pytest.fixture
    def handler(self):
        cfg = MagicMock()
        cfg.browser.screenshot_dir = "/tmp/screenshots"
        return CaptchaHandler(config=cfg)

    @pytest.mark.asyncio
    async def test_detect_no_captcha(self, handler):
        page = AsyncMock()
        page.url = "https://example.com"
        page.query_selector = AsyncMock(return_value=None)

        info = await handler.detect(page)
        assert info.found is False
        assert info.captcha_type == CaptchaType.UNKNOWN

    @pytest.mark.asyncio
    async def test_detect_text_image(self, handler):
        page = AsyncMock()
        page.url = "https://example.com"

        mock_el = AsyncMock()
        mock_el.get_attribute = AsyncMock(return_value="captcha_img_123")

        async def query_side_effect(sel):
            if "captcha" in sel.lower() and "iframe" not in sel and "recaptcha" not in sel:
                return mock_el
            return None

        page.query_selector = query_side_effect

        info = await handler.detect(page)
        # May detect as TEXT_IMAGE depending on selector priority
        assert info.found is True


class TestCaptchaHandlerSolve:
    """Test CaptchaHandler.solve()."""

    @pytest.fixture
    def handler(self):
        cfg = MagicMock()
        cfg.browser.screenshot_dir = "/tmp/screenshots"
        return CaptchaHandler(config=cfg)

    @pytest.mark.asyncio
    async def test_solve_no_captcha(self, handler):
        page = AsyncMock()
        page.url = "https://example.com"
        page.query_selector = AsyncMock(return_value=None)

        result = await handler.solve(page)
        assert result.success is True
        assert result.error == "No CAPTCHA found"

    @pytest.mark.asyncio
    async def test_solve_with_provided_info(self, handler):
        page = AsyncMock()
        page.url = "https://example.com"

        info = CaptchaInfo(found=False)
        result = await handler.solve(page, captcha_info=info)
        assert result.success is True


# ═══════════════════════════════════════════════════════════════════════════════
# Strategy classes
# ═══════════════════════════════════════════════════════════════════════════════

class TestOcrStrategy:
    """Test OcrStrategy."""

    def test_is_available_callable(self):
        assert callable(OcrStrategy.is_available)

    def test_solve_callable(self):
        assert callable(OcrStrategy.solve)


class TestPaidServiceStrategy:
    """Test PaidServiceStrategy."""

    def test_init_2captcha(self):
        svc = PaidServiceStrategy(service="2captcha", api_key="fake")
        assert svc.service == "2captcha"
        assert svc.base_url == "https://2captcha.com"

    def test_init_anticaptcha(self):
        svc = PaidServiceStrategy(service="anticaptcha", api_key="fake")
        assert svc.service == "anticaptcha"
        assert svc.base_url == "https://api.anti-captcha.com"

    def test_init_invalid(self):
        with pytest.raises(ValueError, match="Unsupported service"):
            PaidServiceStrategy(service="invalid", api_key="fake")

    def test_total_cost_initially_zero(self):
        svc = PaidServiceStrategy(service="2captcha", api_key="fake")
        assert svc.total_cost == 0.0

    def test_total_cost_tracks(self):
        svc = PaidServiceStrategy(service="2captcha", api_key="fake")
        svc._cost_tracker = [0.003, 0.005]
        assert svc.total_cost == 0.008

    def test_solve_text_captcha_callable(self):
        svc = PaidServiceStrategy(service="2captcha", api_key="fake")
        assert callable(svc.solve_text_captcha)

    def test_solve_recaptcha_v2_callable(self):
        svc = PaidServiceStrategy(service="2captcha", api_key="fake")
        assert callable(svc.solve_recaptcha_v2)


class TestManualStrategy:
    """Test ManualStrategy."""

    def test_init_creates_queue_dir(self, tmp_path):
        queue_dir = tmp_path / "captcha_queue"
        svc = ManualStrategy(queue_dir=str(queue_dir))
        assert queue_dir.exists()

    def test_init_with_notifier(self, tmp_path):
        queue_dir = tmp_path / "captcha_queue"
        notifier = MagicMock()
        svc = ManualStrategy(queue_dir=str(queue_dir), notifier=notifier)
        assert svc._notifier is notifier

    def test_solve_callable(self, tmp_path):
        queue_dir = tmp_path / "captcha_queue"
        svc = ManualStrategy(queue_dir=str(queue_dir))
        assert callable(svc.solve)


# ═══════════════════════════════════════════════════════════════════════════════
# Image Preprocessing Pipeline
# ═══════════════════════════════════════════════════════════════════════════════

from src.browser.image_preprocessing import (
    PreprocessedImage,
    PipelineStep,
    DEFAULT_PIPELINES,
    run_pipeline,
    preprocess_all,
    auto_preprocess,
)


class TestImagePreprocessing:
    """Test image preprocessing module."""

    def test_preprocessed_image_dataclass(self):
        pi = PreprocessedImage()
        assert pi.original is None
        assert pi.processed is None
        assert pi.steps_applied == []
        assert pi.segments == []

    def test_pipeline_step_dataclass(self):
        step = PipelineStep("grayscale", "to_grayscale")
        assert step.name == "grayscale"
        assert step.func == "to_grayscale"
        assert step.kwargs == {}

    def test_pipeline_step_with_kwargs(self):
        step = PipelineStep("blur", "gaussian_blur", {"kernel": 5})
        assert step.kwargs == {"kernel": 5}

    def test_default_pipelines_not_empty(self):
        assert len(DEFAULT_PIPELINES) >= 3

    def test_default_pipelines_start_with_grayscale_or_color_filter(self):
        valid_first_steps = {"to_grayscale", "remove_colored_lines"}
        for pipeline in DEFAULT_PIPELINES:
            assert pipeline[0].func in valid_first_steps, (
                f"Pipeline should start with grayscale or color filter, got {pipeline[0].func}"
            )

    def test_pipeline_functions_exist(self):
        """Verify all pipeline step functions are importable."""
        import importlib
        mod = importlib.import_module("src.browser.image_preprocessing")
        for pipeline in DEFAULT_PIPELINES:
            for step in pipeline:
                func = getattr(mod, step.func, None)
                assert func is not None, f"Function '{step.func}' not found in image_preprocessing module"
                assert callable(func)

    def test_run_pipeline_callable(self):
        assert callable(run_pipeline)

    def test_preprocess_all_callable(self):
        assert callable(preprocess_all)

    def test_auto_preprocess_callable(self):
        assert callable(auto_preprocess)
