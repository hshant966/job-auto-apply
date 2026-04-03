"""Fingerprint Profiles — Real browser fingerprint database.

Provides complete, realistic browser fingerprint profiles that match
actual hardware/software combinations found in the wild. Each profile
includes all fingerprintable attributes used by anti-bot systems.

Profiles are based on real-world browser fingerprint data collected from
analytics platforms and anti-fingerprint research papers.
"""

from __future__ import annotations

import hashlib
import json
import random
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional


@dataclass
class WebGLProfile:
    """WebGL fingerprint attributes."""
    vendor: str
    renderer: str
    unmasked_vendor: str
    unmasked_renderer: str
    # Supported extensions (subset for realism)
    extensions: list[str] = field(default_factory=list)
    max_texture_size: int = 16384
    max_renderbuffer_size: int = 16384
    max_viewport_dims: tuple[int, int] = (16384, 16384)
    aliased_line_width_range: tuple[float, float] = (1.0, 1.0)
    aliased_point_size_range: tuple[float, float] = (1.0, 1024.0)


@dataclass
class CanvasProfile:
    """Canvas fingerprint seed for consistent noise."""
    seed: int  # Deterministic seed for noise generation
    noise_level: int = 3  # Pixel variation range (+/-)


@dataclass
class AudioProfile:
    """AudioContext fingerprint attributes."""
    noise_level: float = 1e-7  # Small noise on frequency data
    sample_rate: float = 44100.0
    channel_count: int = 2


@dataclass
class ScreenProfile:
    """Screen/display attributes."""
    width: int
    height: int
    avail_width: int
    avail_height: int
    color_depth: int
    pixel_depth: int
    device_pixel_ratio: float
    # Physical screen characteristics
    physical_width_mm: float = 0.0
    physical_height_mm: float = 0.0


@dataclass
class NavigatorProfile:
    """Navigator object attributes."""
    platform: str
    hardware_concurrency: int
    device_memory: int  # GB
    max_touch_points: int = 0
    # Language settings
    language: str = "en-US"
    languages: list[str] = field(default_factory=lambda: ["en-US", "en"])
    # Do Not Track
    do_not_track: str = "1"


@dataclass
class FontProfile:
    """Installed fonts list (common subset)."""
    fonts: list[str] = field(default_factory=list)


@dataclass
class ChromeProfile:
    """Chrome-specific attributes."""
    version: str  # e.g., "131.0.6778.85"
    major_version: int  # e.g., 131
    ua_version: str  # e.g., "131.0.0.0" (in UA string)


@dataclass
class FingerprintProfile:
    """Complete browser fingerprint profile."""
    name: str
    description: str
    browser: ChromeProfile
    user_agent: str
    viewport: ScreenProfile
    navigator: NavigatorProfile
    webgl: WebGLProfile
    canvas: CanvasProfile
    audio: AudioProfile
    fonts: FontProfile
    # TLS characteristics
    tls_version: str = "tls_1_3"
    # Timing
    timezone: str = "America/New_York"
    locale: str = "en-US"
    # Touch
    touch_support: bool = False

    def get_noise_seed(self, page_url: str = "") -> int:
        """Generate a deterministic seed from profile + URL for consistent fingerprints."""
        key = f"{self.name}:{self.canvas.seed}:{page_url}"
        return int(hashlib.md5(key.encode()).hexdigest()[:8], 16)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        return asdict(self)


# ============================================================================
# Real GPU Strings Database (from actual hardware)
# ============================================================================

REAL_WEBGL_GPUS: list[WebGLProfile] = [
    WebGLProfile(
        vendor="WebKit",
        renderer="WebKit WebGL",
        unmasked_vendor="Google Inc. (Intel)",
        unmasked_renderer="ANGLE (Intel, Intel(R) UHD Graphics 630 (0x00003E9B) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        extensions=[
            "ANGLE_instanced_arrays", "EXT_blend_minmax", "EXT_color_buffer_half_float",
            "EXT_disjoint_timer_query", "EXT_float_blend", "EXT_frag_depth",
            "EXT_shader_texture_lod", "EXT_texture_compression_bptc",
            "EXT_texture_compression_rgtc", "EXT_texture_filter_anisotropic",
            "OES_element_index_uint", "OES_fbo_render_mipmap",
            "OES_standard_derivatives", "OES_texture_float",
            "OES_texture_float_linear", "OES_texture_half_float",
            "OES_texture_half_float_linear", "OES_vertex_array_object",
            "WEBGL_color_buffer_float", "WEBGL_compressed_texture_s3tc",
            "WEBGL_compressed_texture_s3tc_srgb", "WEBGL_debug_renderer_info",
            "WEBGL_debug_shaders", "WEBGL_depth_texture",
            "WEBGL_draw_buffers", "WEBGL_lose_context",
        ],
        max_texture_size=16384,
        max_renderbuffer_size=16384,
    ),
    WebGLProfile(
        vendor="WebKit",
        renderer="WebKit WebGL",
        unmasked_vendor="Google Inc. (NVIDIA)",
        unmasked_renderer="ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 SUPER Direct3D11 vs_5_0 ps_5_0, D3D11)",
        extensions=[
            "ANGLE_instanced_arrays", "EXT_blend_minmax", "EXT_color_buffer_half_float",
            "EXT_disjoint_timer_query", "EXT_float_blend", "EXT_frag_depth",
            "EXT_shader_texture_lod", "EXT_texture_compression_bptc",
            "EXT_texture_compression_rgtc", "EXT_texture_filter_anisotropic",
            "EXT_sRGB", "OES_element_index_uint", "OES_fbo_render_mipmap",
            "OES_standard_derivatives", "OES_texture_float",
            "OES_texture_float_linear", "OES_texture_half_float",
            "OES_texture_half_float_linear", "OES_vertex_array_object",
            "WEBGL_color_buffer_float", "WEBGL_compressed_texture_s3tc",
            "WEBGL_compressed_texture_s3tc_srgb", "WEBGL_debug_renderer_info",
            "WEBGL_debug_shaders", "WEBGL_depth_texture",
            "WEBGL_draw_buffers", "WEBGL_lose_context",
        ],
        max_texture_size=16384,
        max_renderbuffer_size=16384,
    ),
    WebGLProfile(
        vendor="WebKit",
        renderer="WebKit WebGL",
        unmasked_vendor="Google Inc. (NVIDIA)",
        unmasked_renderer="ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        extensions=[
            "ANGLE_instanced_arrays", "EXT_blend_minmax", "EXT_color_buffer_half_float",
            "EXT_disjoint_timer_query", "EXT_float_blend", "EXT_frag_depth",
            "EXT_shader_texture_lod", "EXT_texture_compression_bptc",
            "EXT_texture_compression_rgtc", "EXT_texture_filter_anisotropic",
            "EXT_sRGB", "KHR_parallel_shader_compile",
            "OES_element_index_uint", "OES_fbo_render_mipmap",
            "OES_standard_derivatives", "OES_texture_float",
            "OES_texture_float_linear", "OES_texture_half_float",
            "OES_texture_half_float_linear", "OES_vertex_array_object",
            "WEBGL_color_buffer_float", "WEBGL_compressed_texture_s3tc",
            "WEBGL_compressed_texture_s3tc_srgb", "WEBGL_debug_renderer_info",
            "WEBGL_debug_shaders", "WEBGL_depth_texture",
            "WEBGL_draw_buffers", "WEBGL_lose_context",
        ],
        max_texture_size=16384,
        max_renderbuffer_size=16384,
    ),
    WebGLProfile(
        vendor="WebKit",
        renderer="WebKit WebGL",
        unmasked_vendor="Google Inc. (Apple)",
        unmasked_renderer="ANGLE (Apple, Apple M1, OpenGL 4.1)",
        extensions=[
            "ANGLE_instanced_arrays", "EXT_blend_minmax", "EXT_color_buffer_half_float",
            "EXT_disjoint_timer_query", "EXT_float_blend", "EXT_frag_depth",
            "EXT_shader_texture_lod", "EXT_texture_compression_bptc",
            "EXT_texture_compression_rgtc", "EXT_texture_filter_anisotropic",
            "EXT_sRGB", "OES_element_index_uint", "OES_fbo_render_mipmap",
            "OES_standard_derivatives", "OES_texture_float",
            "OES_texture_float_linear", "OES_texture_half_float",
            "OES_texture_half_float_linear", "OES_vertex_array_object",
            "WEBGL_color_buffer_float", "WEBGL_compressed_texture_s3tc",
            "WEBGL_compressed_texture_s3tc_srgb", "WEBGL_debug_renderer_info",
            "WEBGL_debug_shaders", "WEBGL_depth_texture",
            "WEBGL_draw_buffers", "WEBGL_lose_context",
        ],
        max_texture_size=16384,
        max_renderbuffer_size=16384,
    ),
    WebGLProfile(
        vendor="WebKit",
        renderer="WebKit WebGL",
        unmasked_vendor="Google Inc. (AMD)",
        unmasked_renderer="ANGLE (AMD, AMD Radeon RX 580 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        extensions=[
            "ANGLE_instanced_arrays", "EXT_blend_minmax", "EXT_color_buffer_half_float",
            "EXT_disjoint_timer_query", "EXT_float_blend", "EXT_frag_depth",
            "EXT_shader_texture_lod", "EXT_texture_compression_bptc",
            "EXT_texture_compression_rgtc", "EXT_texture_filter_anisotropic",
            "OES_element_index_uint", "OES_fbo_render_mipmap",
            "OES_standard_derivatives", "OES_texture_float",
            "OES_texture_float_linear", "OES_texture_half_float",
            "OES_texture_half_float_linear", "OES_vertex_array_object",
            "WEBGL_color_buffer_float", "WEBGL_compressed_texture_s3tc",
            "WEBGL_compressed_texture_s3tc_srgb", "WEBGL_debug_renderer_info",
            "WEBGL_debug_shaders", "WEBGL_depth_texture",
            "WEBGL_draw_buffers", "WEBGL_lose_context",
        ],
        max_texture_size=16384,
        max_renderbuffer_size=16384,
    ),
    WebGLProfile(
        vendor="WebKit",
        renderer="WebKit WebGL",
        unmasked_vendor="Google Inc. (Intel)",
        unmasked_renderer="ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)",
        extensions=[
            "ANGLE_instanced_arrays", "EXT_blend_minmax", "EXT_color_buffer_half_float",
            "EXT_disjoint_timer_query", "EXT_float_blend", "EXT_frag_depth",
            "EXT_shader_texture_lod", "EXT_texture_compression_bptc",
            "EXT_texture_compression_rgtc", "EXT_texture_filter_anisotropic",
            "OES_element_index_uint", "OES_fbo_render_mipmap",
            "OES_standard_derivatives", "OES_texture_float",
            "OES_texture_float_linear", "OES_texture_half_float",
            "OES_texture_half_float_linear", "OES_vertex_array_object",
            "WEBGL_color_buffer_float", "WEBGL_compressed_texture_s3tc",
            "WEBGL_compressed_texture_s3tc_srgb", "WEBGL_debug_renderer_info",
            "WEBGL_debug_shaders", "WEBGL_depth_texture",
            "WEBGL_draw_buffers", "WEBGL_lose_context",
        ],
        max_texture_size=16384,
        max_renderbuffer_size=16384,
    ),
    WebGLProfile(
        vendor="WebKit",
        renderer="WebKit WebGL",
        unmasked_vendor="Google Inc. (NVIDIA)",
        unmasked_renderer="ANGLE (NVIDIA, NVIDIA GeForce RTX 4070 Ti, Vulkan 1.3.271)",
        extensions=[
            "ANGLE_instanced_arrays", "EXT_blend_minmax", "EXT_color_buffer_half_float",
            "EXT_disjoint_timer_query", "EXT_float_blend", "EXT_frag_depth",
            "EXT_shader_texture_lod", "EXT_texture_compression_astc",
            "EXT_texture_compression_bptc", "EXT_texture_compression_rgtc",
            "EXT_texture_filter_anisotropic", "EXT_sRGB",
            "KHR_parallel_shader_compile",
            "OES_element_index_uint", "OES_fbo_render_mipmap",
            "OES_standard_derivatives", "OES_texture_float",
            "OES_texture_float_linear", "OES_texture_half_float",
            "OES_texture_half_float_linear", "OES_vertex_array_object",
            "WEBGL_color_buffer_float", "WEBGL_compressed_texture_s3tc",
            "WEBGL_compressed_texture_s3tc_srgb", "WEBGL_debug_renderer_info",
            "WEBGL_debug_shaders", "WEBGL_depth_texture",
            "WEBGL_draw_buffers", "WEBGL_lose_context",
        ],
        max_texture_size=16384,
        max_renderbuffer_size=16384,
    ),
    WebGLProfile(
        vendor="WebKit",
        renderer="WebKit WebGL",
        unmasked_vendor="Google Inc. (Apple)",
        unmasked_renderer="ANGLE (Apple, Apple M2 Pro, OpenGL 4.1)",
        extensions=[
            "ANGLE_instanced_arrays", "EXT_blend_minmax", "EXT_color_buffer_half_float",
            "EXT_disjoint_timer_query", "EXT_float_blend", "EXT_frag_depth",
            "EXT_shader_texture_lod", "EXT_texture_compression_bptc",
            "EXT_texture_compression_rgtc", "EXT_texture_filter_anisotropic",
            "EXT_sRGB", "OES_element_index_uint", "OES_fbo_render_mipmap",
            "OES_standard_derivatives", "OES_texture_float",
            "OES_texture_float_linear", "OES_texture_half_float",
            "OES_texture_half_float_linear", "OES_vertex_array_object",
            "WEBGL_color_buffer_float", "WEBGL_compressed_texture_s3tc",
            "WEBGL_compressed_texture_s3tc_srgb", "WEBGL_debug_renderer_info",
            "WEBGL_debug_shaders", "WEBGL_depth_texture",
            "WEBGL_draw_buffers", "WEBGL_lose_context",
        ],
        max_texture_size=16384,
        max_renderbuffer_size=16384,
    ),
]


# ============================================================================
# Real Chrome Profiles — Complete fingerprint profiles
# ============================================================================

PROFILE_DATABASE: list[FingerprintProfile] = [
    # ── Profile 1: Windows 10 Desktop, Intel UHD 630 ──────────────────
    FingerprintProfile(
        name="win10-intel-630",
        description="Windows 10 Desktop - Intel UHD 630 - Chrome 131",
        browser=ChromeProfile(
            version="131.0.6778.85",
            major_version=131,
            ua_version="131.0.0.0",
        ),
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        viewport=ScreenProfile(
            width=1920, height=1080,
            avail_width=1920, avail_height=1040,
            color_depth=24, pixel_depth=24,
            device_pixel_ratio=1.0,
        ),
        navigator=NavigatorProfile(
            platform="Win32",
            hardware_concurrency=8,
            device_memory=16,
        ),
        webgl=REAL_WEBGL_GPUS[0],
        canvas=CanvasProfile(seed=2847561, noise_level=3),
        audio=AudioProfile(noise_level=1.2e-7, sample_rate=44100.0),
        fonts=FontProfile(fonts=[
            "Arial", "Calibri", "Cambria", "Comic Sans MS", "Consolas",
            "Courier New", "Georgia", "Impact", "Lucida Console",
            "Microsoft Sans Serif", "Palatino Linotype", "Segoe UI",
            "Tahoma", "Times New Roman", "Trebuchet MS", "Verdana",
            "Wingdings", "MS Gothic", "PMingLiU", "SimSun",
        ]),
        timezone="America/New_York",
        locale="en-US",
    ),
    # ── Profile 2: Windows 11 Desktop, NVIDIA GTX 1660S ───────────────
    FingerprintProfile(
        name="win11-nvidia-1660s",
        description="Windows 11 Desktop - NVIDIA GTX 1660 SUPER - Chrome 131",
        browser=ChromeProfile(
            version="131.0.6778.85",
            major_version=131,
            ua_version="131.0.0.0",
        ),
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        viewport=ScreenProfile(
            width=2560, height=1440,
            avail_width=2560, avail_height=1400,
            color_depth=24, pixel_depth=24,
            device_pixel_ratio=1.25,
        ),
        navigator=NavigatorProfile(
            platform="Win32",
            hardware_concurrency=12,
            device_memory=32,
        ),
        webgl=REAL_WEBGL_GPUS[1],
        canvas=CanvasProfile(seed=9182734, noise_level=3),
        audio=AudioProfile(noise_level=0.8e-7, sample_rate=48000.0),
        fonts=FontProfile(fonts=[
            "Arial", "Calibri", "Cambria", "Cambria Math", "Comic Sans MS",
            "Consolas", "Courier New", "Ebrima", "Franklin Gothic Medium",
            "Gabriola", "Georgia", "Impact", "Leelawadee UI",
            "Lucida Console", "Malgun Gothic", "Microsoft Himalaya",
            "Microsoft JhengHei", "Microsoft Sans Serif", "MingLiU",
            "Mongolian Baiti", "MS Gothic", "MV Boli", "Nirmala UI",
            "Palatino Linotype", "Segoe UI", "Segoe UI Emoji",
            "Segoe UI Historic", "Segoe UI Symbol", "SimSun",
            "Tahoma", "Times New Roman", "Trebuchet MS", "Verdana",
        ]),
        timezone="America/Chicago",
        locale="en-US",
    ),
    # ── Profile 3: macOS, Apple M1 ────────────────────────────────────
    FingerprintProfile(
        name="macos-m1-chrome",
        description="macOS Ventura - Apple M1 - Chrome 131",
        browser=ChromeProfile(
            version="131.0.6778.86",
            major_version=131,
            ua_version="131.0.0.0",
        ),
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        viewport=ScreenProfile(
            width=1440, height=900,
            avail_width=1440, avail_height=875,
            color_depth=24, pixel_depth=24,
            device_pixel_ratio=2.0,
        ),
        navigator=NavigatorProfile(
            platform="MacIntel",
            hardware_concurrency=8,
            device_memory=8,
        ),
        webgl=REAL_WEBGL_GPUS[3],
        canvas=CanvasProfile(seed=5619273, noise_level=3),
        audio=AudioProfile(noise_level=1.5e-7, sample_rate=44100.0),
        fonts=FontProfile(fonts=[
            "American Typewriter", "Andale Mono", "Arial", "Arial Black",
            "Arial Narrow", "Arial Rounded MT Bold", "Avenir",
            "Avenir Next", "Avenir Next Condensed", "Baskerville",
            "Big Caslon", "Bodoni 72", "Bradley Hand", "Chalkboard",
            "Chalkboard SE", "Chalkduster", "Cochin", "Comic Sans MS",
            "Copperplate", "Courier", "Courier New", "Didot",
            "DIN Alternate", "DIN Condensed", "Futura", "Geneva",
            "Georgia", "Gill Sans", "Helvetica", "Helvetica Neue",
            "Herculanum", "Hoefler Text", "Impact", "Lucida Grande",
            "Luminari", "Marker Felt", "Menlo", "Monaco",
            "Noteworthy", "Optima", "Palatino", "Papyrus",
            "Phosphate", "Rockwell", "Sathu", "Silom",
            "Snell Roundhand", "Tahoma", "Times", "Times New Roman",
            "Trattatello", "Trebuchet MS", "Verdana", "Zapfino",
        ]),
        timezone="America/Los_Angeles",
        locale="en-US",
    ),
    # ── Profile 4: Windows 10, AMD RX 580 ─────────────────────────────
    FingerprintProfile(
        name="win10-amd-580",
        description="Windows 10 Desktop - AMD Radeon RX 580 - Chrome 130",
        browser=ChromeProfile(
            version="130.0.6723.92",
            major_version=130,
            ua_version="130.0.0.0",
        ),
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        viewport=ScreenProfile(
            width=1920, height=1080,
            avail_width=1920, avail_height=1040,
            color_depth=24, pixel_depth=24,
            device_pixel_ratio=1.0,
        ),
        navigator=NavigatorProfile(
            platform="Win32",
            hardware_concurrency=6,
            device_memory=16,
        ),
        webgl=REAL_WEBGL_GPUS[4],
        canvas=CanvasProfile(seed=7483921, noise_level=4),
        audio=AudioProfile(noise_level=2.0e-7, sample_rate=44100.0),
        fonts=FontProfile(fonts=[
            "Arial", "Calibri", "Cambria", "Comic Sans MS", "Consolas",
            "Courier New", "Georgia", "Impact", "Lucida Console",
            "Microsoft Sans Serif", "Palatino Linotype", "Segoe UI",
            "Tahoma", "Times New Roman", "Trebuchet MS", "Verdana",
        ]),
        timezone="America/Denver",
        locale="en-US",
    ),
    # ── Profile 5: Linux, Intel Iris Xe (laptop) ──────────────────────
    FingerprintProfile(
        name="linux-intel-irisxe",
        description="Ubuntu 22.04 Laptop - Intel Iris Xe - Chrome 131",
        browser=ChromeProfile(
            version="131.0.6778.85",
            major_version=131,
            ua_version="131.0.0.0",
        ),
        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        viewport=ScreenProfile(
            width=1366, height=768,
            avail_width=1366, avail_height=728,
            color_depth=24, pixel_depth=24,
            device_pixel_ratio=1.0,
        ),
        navigator=NavigatorProfile(
            platform="Linux x86_64",
            hardware_concurrency=8,
            device_memory=8,
        ),
        webgl=REAL_WEBGL_GPUS[5],
        canvas=CanvasProfile(seed=3928174, noise_level=3),
        audio=AudioProfile(noise_level=1.0e-7, sample_rate=44100.0),
        fonts=FontProfile(fonts=[
            "DejaVu Sans", "DejaVu Sans Mono", "DejaVu Serif",
            "Droid Sans", "FreeMono", "FreeSans", "FreeSerif",
            "Liberation Mono", "Liberation Sans", "Liberation Serif",
            "Noto Sans", "Noto Serif", "Ubuntu", "Ubuntu Condensed",
            "Ubuntu Mono", "Arial", "Courier New", "Georgia",
            "Times New Roman", "Verdana", "Webdings",
        ]),
        timezone="America/New_York",
        locale="en-US",
    ),
    # ── Profile 6: Windows 11, RTX 4070 Ti (high-end) ─────────────────
    FingerprintProfile(
        name="win11-rtx4070ti",
        description="Windows 11 Desktop - NVIDIA RTX 4070 Ti - Chrome 131",
        browser=ChromeProfile(
            version="131.0.6778.108",
            major_version=131,
            ua_version="131.0.0.0",
        ),
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        viewport=ScreenProfile(
            width=2560, height=1440,
            avail_width=2560, avail_height=1400,
            color_depth=24, pixel_depth=24,
            device_pixel_ratio=1.0,
        ),
        navigator=NavigatorProfile(
            platform="Win32",
            hardware_concurrency=16,
            device_memory=32,
        ),
        webgl=REAL_WEBGL_GPUS[6],
        canvas=CanvasProfile(seed=6174829, noise_level=3),
        audio=AudioProfile(noise_level=0.5e-7, sample_rate=48000.0),
        fonts=FontProfile(fonts=[
            "Arial", "Calibri", "Cambria", "Cambria Math", "Candara",
            "Comic Sans MS", "Consolas", "Constantia", "Corbel",
            "Courier New", "Ebrima", "Franklin Gothic Medium",
            "Gabriola", "Gadugi", "Georgia", "Impact",
            "Ink Free", "Javanese Text", "Leelawadee UI",
            "Lucida Console", "Lucida Sans Unicode", "Malgun Gothic",
            "Microsoft Himalaya", "Microsoft JhengHei", "Microsoft New Tai Lue",
            "Microsoft PhagsPa", "Microsoft Sans Serif", "Microsoft Tai Le",
            "Microsoft YaHei", "Microsoft Yi Baiti", "MingLiU",
            "Mongolian Baiti", "MS Gothic", "MV Boli", "Nirmala UI",
            "Palatino Linotype", "Segoe Print", "Segoe Script",
            "Segoe UI", "Segoe UI Emoji", "Segoe UI Historic",
            "Segoe UI Symbol", "SimSun", "Sitka", "Sylfaen",
            "Symbol", "Tahoma", "Times New Roman", "Trebuchet MS",
            "Verdana", "Webdings", "Wingdings", "Yu Gothic",
        ]),
        timezone="America/New_York",
        locale="en-US",
    ),
    # ── Profile 7: macOS, Apple M2 Pro ────────────────────────────────
    FingerprintProfile(
        name="macos-m2pro-chrome",
        description="macOS Sonoma - Apple M2 Pro - Chrome 131",
        browser=ChromeProfile(
            version="131.0.6778.86",
            major_version=131,
            ua_version="131.0.0.0",
        ),
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        viewport=ScreenProfile(
            width=1728, height=1117,
            avail_width=1728, avail_height=1092,
            color_depth=24, pixel_depth=24,
            device_pixel_ratio=2.0,
        ),
        navigator=NavigatorProfile(
            platform="MacIntel",
            hardware_concurrency=12,
            device_memory=16,
        ),
        webgl=REAL_WEBGL_GPUS[7],
        canvas=CanvasProfile(seed=4502817, noise_level=3),
        audio=AudioProfile(noise_level=1.1e-7, sample_rate=48000.0),
        fonts=FontProfile(fonts=[
            "American Typewriter", "Andale Mono", "Arial", "Arial Black",
            "Arial Hebrew", "Arial Narrow", "Avenir", "Avenir Next",
            "Avenir Next Condensed", "Baskerville", "Big Caslon",
            "Bodoni 72", "Bradley Hand", "Brush Script MT",
            "Chalkboard", "Chalkboard SE", "Chalkduster", "Charter",
            "Cochin", "Comic Sans MS", "Copperplate", "Courier",
            "Courier New", "Didot", "DIN Alternate", "DIN Condensed",
            "Futura", "Galvji", "Geneva", "Georgia", "Gill Sans",
            "Helvetica", "Helvetica Neue", "Herculanum",
            "Hoefler Text", "Impact", "Kohinoor Telugu",
            "Lucida Grande", "Luminari", "Marker Felt", "Menlo",
            "Monaco", "Noteworthy", "Optima", "Palatino",
            "Papyrus", "Phosphate", "Rockwell", "Sathu",
            "Savoye LET", "Seravek", "Silom", "Sitka",
            "Snell Roundhand", "Symbol", "Tahoma", "Times",
            "Times New Roman", "Trattatello", "Trebuchet MS",
            "Verdana", "Zapfino",
        ]),
        timezone="America/Los_Angeles",
        locale="en-US",
    ),
]


class FingerprintProfileManager:
    """Manages fingerprint profile selection and consistency.

    Profiles can be selected randomly, by name, or by matching criteria.
    Once a profile is selected for a session, all attributes remain consistent.
    """

    def __init__(self, profiles: list[FingerprintProfile] | None = None):
        self._profiles = profiles or PROFILE_DATABASE.copy()
        self._active_profile: FingerprintProfile | None = None
        self._profile_index: dict[str, FingerprintProfile] = {
            p.name: p for p in self._profiles
        }

    @property
    def active_profile(self) -> FingerprintProfile:
        """Get the currently active profile, selecting one if needed."""
        if self._active_profile is None:
            self._active_profile = random.choice(self._profiles)
        return self._active_profile

    def select_random(self) -> FingerprintProfile:
        """Select a random profile."""
        self._active_profile = random.choice(self._profiles)
        return self._active_profile

    def select_by_name(self, name: str) -> FingerprintProfile:
        """Select a profile by name."""
        if name not in self._profile_index:
            available = ", ".join(self._profile_index.keys())
            raise ValueError(f"Profile '{name}' not found. Available: {available}")
        self._active_profile = self._profile_index[name]
        return self._active_profile

    def select_by_os(self, os_filter: str) -> FingerprintProfile:
        """Select a profile matching an OS filter (win/mac/linux)."""
        os_lower = os_filter.lower()
        matches = [
            p for p in self._profiles
            if os_lower in p.name.lower()
        ]
        if not matches:
            matches = self._profiles
        self._active_profile = random.choice(matches)
        return self._active_profile

    def list_profiles(self) -> list[dict[str, str]]:
        """List all available profiles."""
        return [
            {"name": p.name, "description": p.description}
            for p in self._profiles
        ]

    def add_profile(self, profile: FingerprintProfile):
        """Add a custom profile to the database."""
        self._profiles.append(profile)
        self._profile_index[profile.name] = profile

    def get_js_overrides(self, page_url: str = "") -> str:
        """Generate JavaScript code to override browser attributes based on active profile."""
        p = self.active_profile
        seed = p.get_noise_seed(page_url)

        return f"""
// === Fingerprint Profile: {p.name} ===
(function() {{
    'use strict';

    const SEED = {seed};
    const PROFILE = {json.dumps(p.to_dict())};

    // -- Navigator overrides --
    Object.defineProperty(navigator, 'hardwareConcurrency', {{
        get: () => {p.navigator.hardware_concurrency}
    }});
    Object.defineProperty(navigator, 'deviceMemory', {{
        get: () => {p.navigator.device_memory}
    }});
    Object.defineProperty(navigator, 'platform', {{
        get: () => '{p.navigator.platform}'
    }});
    Object.defineProperty(navigator, 'maxTouchPoints', {{
        get: () => {p.navigator.max_touch_points}
    }});
    Object.defineProperty(navigator, 'language', {{
        get: () => '{p.navigator.language}'
    }});
    Object.defineProperty(navigator, 'languages', {{
        get: () => {json.dumps(p.navigator.languages)}
    }});
    Object.defineProperty(navigator, 'doNotTrack', {{
        get: () => '{p.navigator.do_not_track}'
    }});

    // -- Screen overrides --
    Object.defineProperty(screen, 'width', {{ get: () => {p.viewport.width} }});
    Object.defineProperty(screen, 'height', {{ get: () => {p.viewport.height} }});
    Object.defineProperty(screen, 'availWidth', {{ get: () => {p.viewport.avail_width} }});
    Object.defineProperty(screen, 'availHeight', {{ get: () => {p.viewport.avail_height} }});
    Object.defineProperty(screen, 'colorDepth', {{ get: () => {p.viewport.color_depth} }});
    Object.defineProperty(screen, 'pixelDepth', {{ get: () => {p.viewport.pixel_depth} }});

    // -- WebGL overrides (masked vendor/renderer) --
    const UNMASKED_VENDOR = {json.dumps(p.webgl.unmasked_vendor)};
    const UNMASKED_RENDERER = {json.dumps(p.webgl.unmasked_renderer)};
    const VENDOR = {json.dumps(p.webgl.vendor)};
    const RENDERER = {json.dumps(p.webgl.renderer)};

    const originalGetParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(param) {{
        if (param === 0x9245) return UNMASKED_VENDOR;   // UNMASKED_VENDOR_WEBGL
        if (param === 0x9246) return UNMASKED_RENDERER;  // UNMASKED_RENDERER_WEBGL
        if (param === 0x1F00) return VENDOR;             // VENDOR
        if (param === 0x1F01) return RENDERER;           // RENDERER
        if (param === 0x0D33) return {p.webgl.max_texture_size}; // MAX_TEXTURE_SIZE
        if (param === 0x84E8) return {p.webgl.max_renderbuffer_size}; // MAX_RENDERBUFFER_SIZE
        return originalGetParameter.call(this, param);
    }};

    // Also override WebGL2
    if (typeof WebGL2RenderingContext !== 'undefined') {{
        const orig2 = WebGL2RenderingContext.prototype.getParameter;
        WebGL2RenderingContext.prototype.getParameter = function(param) {{
            if (param === 0x9245) return UNMASKED_VENDOR;
            if (param === 0x9246) return UNMASKED_RENDERER;
            if (param === 0x1F00) return VENDOR;
            if (param === 0x1F01) return RENDERER;
            if (param === 0x0D33) return {p.webgl.max_texture_size};
            if (param === 0x84E8) return {p.webgl.max_renderbuffer_size};
            return orig2.call(this, param);
        }};
    }}

    // -- Font fingerprint: make available fonts consistent --
    // This is a passive check; we don't override it but ensure the
    // fonts are actually available by not blocking them.

}})();
"""
