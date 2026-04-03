"""Tests for stealth module — fingerprint profiles, TLS fingerprint, StealthManager."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ═══════════════════════════════════════════════════════════════════════════════
# Fingerprint Profiles
# ═══════════════════════════════════════════════════════════════════════════════

from src.browser.fingerprint_profiles import (
    FingerprintProfile,
    FingerprintProfileManager,
    PROFILE_DATABASE,
    REAL_WEBGL_GPUS,
    WebGLProfile,
    CanvasProfile,
    AudioProfile,
    ScreenProfile,
    NavigatorProfile,
    FontProfile,
    ChromeProfile,
)


class TestFingerprintProfileDataclass:
    """Test the FingerprintProfile dataclass."""

    def test_get_noise_seed_deterministic(self):
        profile = PROFILE_DATABASE[0]
        seed1 = profile.get_noise_seed("https://example.com")
        seed2 = profile.get_noise_seed("https://example.com")
        assert seed1 == seed2

    def test_get_noise_seed_different_urls(self):
        profile = PROFILE_DATABASE[0]
        seed1 = profile.get_noise_seed("https://a.com")
        seed2 = profile.get_noise_seed("https://b.com")
        assert seed1 != seed2

    def test_to_dict(self):
        profile = PROFILE_DATABASE[0]
        d = profile.to_dict()
        assert isinstance(d, dict)
        assert "name" in d
        assert "browser" in d
        assert "webgl" in d
        assert "canvas" in d


class TestFingerprintProfileManager:
    """Test FingerprintProfileManager selection methods."""

    @pytest.fixture
    def mgr(self):
        return FingerprintProfileManager()

    def test_select_random_returns_profile(self, mgr):
        profile = mgr.select_random()
        assert isinstance(profile, FingerprintProfile)
        assert profile.name in mgr._profile_index

    def test_select_random_sets_active(self, mgr):
        profile = mgr.select_random()
        assert mgr._active_profile is profile

    def test_active_profile_lazy_select(self, mgr):
        assert mgr._active_profile is None
        p = mgr.active_profile
        assert isinstance(p, FingerprintProfile)
        assert mgr._active_profile is p

    def test_select_by_name_valid(self, mgr):
        profile = mgr.select_by_name("win10-intel-630")
        assert profile.name == "win10-intel-630"
        assert "Intel" in profile.webgl.unmasked_renderer

    def test_select_by_name_invalid(self, mgr):
        with pytest.raises(ValueError, match="not found"):
            mgr.select_by_name("nonexistent-profile")

    def test_select_by_os_win(self, mgr):
        for _ in range(10):
            profile = mgr.select_by_os("win")
            assert "win" in profile.name.lower()

    def test_select_by_os_mac(self, mgr):
        for _ in range(10):
            profile = mgr.select_by_os("mac")
            assert "mac" in profile.name.lower()

    def test_select_by_os_linux(self, mgr):
        for _ in range(10):
            profile = mgr.select_by_os("linux")
            assert "linux" in profile.name.lower()

    def test_select_by_os_fallback(self, mgr):
        # Unknown OS filter falls back to any profile
        profile = mgr.select_by_os("bsd")
        assert isinstance(profile, FingerprintProfile)

    def test_list_profiles(self, mgr):
        profiles = mgr.list_profiles()
        assert len(profiles) == len(PROFILE_DATABASE)
        assert all("name" in p and "description" in p for p in profiles)

    def test_add_profile(self, mgr):
        custom = FingerprintProfile(
            name="custom-test",
            description="Custom test profile",
            browser=ChromeProfile(version="99.0.0.0", major_version=99, ua_version="99.0.0.0"),
            user_agent="Test/99",
            viewport=ScreenProfile(width=800, height=600, avail_width=800, avail_height=600,
                                   color_depth=24, pixel_depth=24, device_pixel_ratio=1.0),
            navigator=NavigatorProfile(platform="Win32", hardware_concurrency=4, device_memory=8),
            webgl=REAL_WEBGL_GPUS[0],
            canvas=CanvasProfile(seed=12345),
            audio=AudioProfile(),
            fonts=FontProfile(),
        )
        mgr.add_profile(custom)
        assert mgr.select_by_name("custom-test") is custom

    def test_get_js_overrides(self, mgr):
        mgr.select_by_name("win10-intel-630")
        js = mgr.get_js_overrides("https://example.com")
        assert "hardwareConcurrency" in js
        assert "WebGL" in js or "UNMASKED_VENDOR_WEBGL" in js
        assert "win10-intel-630" in js
        assert "defineProperty" in js
        assert "deviceMemory" in js


class TestProfileHardwareConsistency:
    """Test that profiles have internally consistent hardware combos."""

    @pytest.fixture
    def win_profiles(self):
        return [p for p in PROFILE_DATABASE if "win" in p.name.lower()]

    @pytest.fixture
    def mac_profiles(self):
        return [p for p in PROFILE_DATABASE if "mac" in p.name.lower()]

    @pytest.fixture
    def linux_profiles(self):
        return [p for p in PROFILE_DATABASE if "linux" in p.name.lower()]

    def test_windows_profiles_have_win32_platform(self, win_profiles):
        for p in win_profiles:
            assert p.navigator.platform == "Win32", (
                f"Profile {p.name} has platform={p.navigator.platform}, expected Win32"
            )

    def test_mac_profiles_have_macintel_platform(self, mac_profiles):
        for p in mac_profiles:
            assert p.navigator.platform == "MacIntel", (
                f"Profile {p.name} has platform={p.navigator.platform}, expected MacIntel"
            )

    def test_linux_profiles_have_linux_platform(self, linux_profiles):
        for p in linux_profiles:
            assert "linux" in p.navigator.platform.lower(), (
                f"Profile {p.name} has platform={p.navigator.platform}, expected Linux"
            )

    def test_intel_gpu_profiles_use_intel_webgl(self):
        for p in PROFILE_DATABASE:
            if "intel" in p.name.lower():
                assert "Intel" in p.webgl.unmasked_vendor

    def test_nvidia_gpu_profiles_use_nvidia_webgl(self):
        for p in PROFILE_DATABASE:
            if "nvidia" in p.name.lower() or "rtx" in p.name.lower() or "1660" in p.name.lower():
                assert "NVIDIA" in p.webgl.unmasked_renderer

    def test_mac_profiles_use_apple_webgl(self):
        for p in PROFILE_DATABASE:
            if "mac" in p.name.lower():
                assert "Apple" in p.webgl.unmasked_renderer

    def test_amd_gpu_profiles_use_amd_webgl(self):
        for p in PROFILE_DATABASE:
            if "amd" in p.name.lower():
                assert "AMD" in p.webgl.unmasked_renderer

    def test_windows_profiles_have_windows_fonts(self):
        win_profiles = [p for p in PROFILE_DATABASE if "win" in p.name.lower()]
        for p in win_profiles:
            assert "Arial" in p.fonts.fonts
            assert "Segoe UI" in p.fonts.fonts

    def test_mac_profiles_have_mac_fonts(self):
        mac_profiles = [p for p in PROFILE_DATABASE if "mac" in p.name.lower()]
        for p in mac_profiles:
            assert "Helvetica" in p.fonts.fonts

    def test_linux_profiles_have_linux_fonts(self):
        linux_profiles = [p for p in PROFILE_DATABASE if "linux" in p.name.lower()]
        for p in linux_profiles:
            assert "DejaVu Sans" in p.fonts.fonts

    def test_all_profiles_have_valid_viewport(self):
        for p in PROFILE_DATABASE:
            assert p.viewport.width >= 1024
            assert p.viewport.height >= 600
            assert p.viewport.color_depth in (24, 32)

    def test_all_profiles_have_valid_hardware(self):
        for p in PROFILE_DATABASE:
            assert p.navigator.hardware_concurrency >= 4
            assert p.navigator.device_memory >= 4
            assert p.navigator.max_touch_points == 0  # Desktop profiles

    def test_all_profiles_have_tls_13(self):
        for p in PROFILE_DATABASE:
            assert p.tls_version == "tls_1_3"


# ═══════════════════════════════════════════════════════════════════════════════
# TLS Fingerprint Manager
# ═══════════════════════════════════════════════════════════════════════════════

from src.browser.tls_fingerprint import (
    TLSFingerprintManager,
    TLSConfig,
    CHROME_TLS_PROFILES,
    CHROME_CIPHER_SUITES,
    compute_ja3,
    compute_ja4,
    _generate_grease_value,
)


class TestTLSFingerprintManager:
    """Test TLSFingerprintManager."""

    @pytest.fixture
    def tls_mgr(self):
        return TLSFingerprintManager("chrome_131_win")

    def test_init_valid_profile(self):
        mgr = TLSFingerprintManager("chrome_131_win")
        assert mgr._profile_name == "chrome_131_win"

    def test_init_invalid_profile(self):
        with pytest.raises(ValueError, match="Unknown TLS profile"):
            TLSFingerprintManager("firefox_99")

    def test_normalize_headers_lowercase(self, tls_mgr):
        headers = {"Content-Type": "text/html", "ACCEPT": "text/html"}
        normalized = tls_mgr.normalize_headers(headers)
        assert "content-type" in normalized
        assert "accept" in normalized
        assert "Content-Type" not in normalized

    def test_normalize_headers_adds_chrome_sec_headers(self, tls_mgr):
        headers = {"user-agent": "test"}
        normalized = tls_mgr.normalize_headers(headers)
        assert "sec-ch-ua" in normalized
        assert "sec-ch-ua-mobile" in normalized
        assert "sec-ch-ua-platform" in normalized
        assert "sec-fetch-dest" in normalized
        assert "sec-fetch-mode" in normalized
        assert "sec-fetch-site" in normalized
        assert "sec-fetch-user" in normalized
        assert "upgrade-insecure-requests" in normalized
        assert "accept-encoding" in normalized
        assert "accept-language" in normalized

    def test_normalize_headers_removes_playwright(self, tls_mgr):
        headers = {"x-playwright": "true", "user-agent": "test"}
        normalized = tls_mgr.normalize_headers(headers)
        assert "x-playwright" not in normalized

    def test_normalize_headers_preserves_existing_sec_headers(self, tls_mgr):
        headers = {"sec-ch-ua": '"Custom";v="99"'}
        normalized = tls_mgr.normalize_headers(headers)
        assert normalized["sec-ch-ua"] == '"Custom";v="99"'

    def test_get_h2_settings(self, tls_mgr):
        settings = tls_mgr.get_h2_settings()
        assert settings["header_table_size"] == 65536
        assert settings["enable_push"] == 0
        assert settings["max_concurrent_streams"] == 1000
        assert settings["initial_window_size"] == 6291456

    def test_get_init_script(self, tls_mgr):
        script = tls_mgr.get_init_script()
        assert "fetch" in script
        assert "XMLHttpRequest" in script
        assert "sec-ch-ua" in script

    def test_get_playwright_extra_headers(self, tls_mgr):
        headers = tls_mgr.get_playwright_extra_headers()
        assert "sec-ch-ua" in headers
        assert "Chromium" in headers["sec-ch-ua"]
        assert "accept-encoding" in headers
        assert "gzip" in headers["accept-encoding"]

    def test_all_profiles_exist(self):
        for name in CHROME_TLS_PROFILES:
            mgr = TLSFingerprintManager(name)
            assert mgr.config.ja3_hash


class TestJA3JA4:
    """Test JA3/JA4 computation helpers."""

    def test_compute_ja3_format(self):
        ja3 = compute_ja3(
            extensions=[0, 16, 23],
            cipher_suites=[4865, 4866],
            elliptic_curves=[29, 23],
            elliptic_curve_point_formats=[0, 1, 2],
        )
        parts = ja3.split(",")
        assert len(parts) == 5
        assert parts[0] == "771"  # TLS 1.2

    def test_compute_ja4_format(self):
        ja4 = compute_ja4(
            alpn="h2",
            version="13",
            cipher_count=15,
            extension_count=19,
            extensions=[0, 16, 23],
            cipher_suites=[4865, 4866],
        )
        # JA4 format: t{version[0]}{sni}{alpn[0]}{c_count}{e_count}_{hash}_{hash}
        assert ja4.startswith("t1d")  # t=TLS, 1=version[0], d=SNI

    def test_grease_value_pattern(self):
        for _ in range(20):
            val = _generate_grease_value()
            assert (val & 0x0F0F) == 0x0A0A


# ═══════════════════════════════════════════════════════════════════════════════
# Stealth Manager
# ═══════════════════════════════════════════════════════════════════════════════

from src.browser.stealth import (
    StealthManager,
    USER_AGENTS,
    VIEWPORTS,
    STEALTH_JS_TEMPLATE,
)


class TestStealthManager:
    """Test StealthManager class."""

    def test_random_ua_returns_mozilla(self):
        for _ in range(10):
            ua = StealthManager.random_ua()
            assert "Mozilla" in ua

    def test_random_ua_from_pool(self):
        uas = {StealthManager.random_ua() for _ in range(100)}
        assert uas.issubset(set(USER_AGENTS))

    def test_random_viewport_valid(self):
        for _ in range(10):
            w, h = StealthManager.random_viewport()
            assert w >= 1024
            assert h >= 600

    def test_random_viewport_from_pool(self):
        vps = {StealthManager.random_viewport() for _ in range(100)}
        assert vps.issubset(set(VIEWPORTS))

    def test_build_stealth_js_without_profile(self):
        mgr = StealthManager()
        js = mgr._build_stealth_js()
        assert "navigator.webdriver" in js
        assert "window.chrome" in js
        assert "WebGL" in js or "UNMASKED_VENDOR" in js
        assert "AudioContext" in js or "AudioBuffer" in js
        assert "RTCPeerConnection" in js

    def test_build_stealth_js_with_profile(self):
        mgr = StealthManager()
        profile = PROFILE_DATABASE[0]
        mgr.set_profile(profile)
        js = mgr._build_stealth_js()
        assert profile.webgl.unmasked_vendor in js
        assert profile.webgl.unmasked_renderer in js

    def test_stealth_manager_is_callable(self):
        assert callable(StealthManager)
        assert callable(StealthManager.human_delay)
        assert callable(StealthManager.micro_delay)
        assert callable(StealthManager.thinking_delay)
        assert callable(StealthManager.curved_mouse)
        assert callable(StealthManager.human_click)
        assert callable(StealthManager.human_type)
        assert callable(StealthManager.natural_scroll)
        assert callable(StealthManager.random_scroll)
        assert callable(StealthManager.random_mouse_jitter)
        assert callable(StealthManager.tab_switch_simulation)

    @pytest.mark.asyncio
    async def test_human_delay_range(self):
        import time
        start = time.monotonic()
        await StealthManager.human_delay(min_ms=50, max_ms=100)
        elapsed = time.monotonic() - start
        assert 0.04 < elapsed < 0.2  # generous bounds

    @pytest.mark.asyncio
    async def test_micro_delay_range(self):
        import time
        start = time.monotonic()
        await StealthManager.micro_delay(min_ms=10, max_ms=30)
        elapsed = time.monotonic() - start
        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_thinking_delay_range(self):
        import time
        start = time.monotonic()
        await StealthManager.thinking_delay()
        elapsed = time.monotonic() - start
        assert 0.5 < elapsed < 3.0

    def test_stealth_js_template_has_all_detection_vectors(self):
        """Verify the stealth JS covers all 20 documented detection vectors."""
        template = STEALTH_JS_TEMPLATE
        checks = [
            ("navigator.webdriver", "1. navigator.webdriver"),
            ("window.chrome", "2. window.chrome"),
            ("navigator.plugins", "3. navigator.plugins"),
            ("navigator.languages", "4. navigator.languages"),
            ("CanvasRenderingContext2D", "5. Canvas fingerprint"),
            ("UNMASKED_VENDOR_WEBGL", "6. WebGL vendor/renderer"),
            ("AudioBuffer", "7. AudioContext fingerprint"),
            ("RTCPeerConnection", "8. WebRTC"),
            ("navigator.permissions", "9. Permission API"),
            ("contentWindow", "10. iframe contentWindow"),
            ("native code", "11. toString detection"),
            ("getOwnPropertyNames", "12. CDP detection"),
            ("prepareStackTrace", "13. Stack trace"),
            ("enumerateDevices", "14. MediaDevices"),
            ("Notification", "15. Notification API"),
            ("performance.now", "16. Performance timing"),
            ("navigator.connection", "17. Connection API"),
            ("speechSynthesis", "18. Speech synthesis"),
            ("currentScript", "19. document.currentScript"),
            ("outerWidth", "20. Window dimensions"),
        ]
        for keyword, description in checks:
            assert keyword in template, f"Missing detection vector: {description}"
