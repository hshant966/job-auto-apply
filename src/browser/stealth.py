"""Anti-Detection & Stealth v3 — Comprehensive Playwright fingerprint masking.

This module provides next-generation anti-detection for Playwright by patching
ALL known detection vectors used by modern anti-bot systems including:
- Datadome, PerimeterX, Cloudflare, Imperva, Kasada, Shape/F5

Detection vectors covered:
1. navigator.webdriver = true
2. navigator.plugins.length = 0
3. navigator.languages inconsistency
4. window.chrome undefined
5. Canvas fingerprint (randomize pixel data with deterministic noise)
6. WebGL vendor/renderer strings
7. AudioContext fingerprint
8. WebRTC local IP leak
9. Permission API detection
10. iframe contentWindow.chrome
11. toString() override detection (Function.prototype.toString)
12. CDP (Chrome DevTools Protocol) detection
13. Time-based bot detection (too-fast actions)
14. Mouse movement pattern detection
15. TLS fingerprint (JA3/JA4) — delegated to tls_fingerprint module

All patches run BEFORE any page loads via page.add_init_script().
"""

from __future__ import annotations

import asyncio
import logging
import math
import random
import time
from typing import Optional

logger = logging.getLogger(__name__)

# ============================================================================
# Master stealth JavaScript — injected before any page loads
# ============================================================================

STEALTH_JS_TEMPLATE = """
// ╔══════════════════════════════════════════════════════════════╗
// ║  Stealth Module v3 — Comprehensive Anti-Detection           ║
// ║  All patches run in page context BEFORE any page scripts    ║
// ╚══════════════════════════════════════════════════════════════╝
(function() {{
    'use strict';

    // ========================================================================
    // Utility: Seeded PRNG for deterministic fingerprint consistency
    // ========================================================================
    function mulberry32(a) {{
        return function() {{
            a |= 0; a = a + 0x6D2B79F5 | 0;
            var t = Math.imul(a ^ a >>> 15, 1 | a);
            t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
            return ((t ^ t >>> 14) >>> 0) / 4294967296;
        }};
    }}

    const STEALTH_SEED = {canvas_seed};
    const PRNG = mulberry32(STEALTH_SEED);

    // ========================================================================
    // 1. navigator.webdriver — the #1 detection vector
    // ========================================================================
    Object.defineProperty(navigator, 'webdriver', {{
        get: () => undefined,
        configurable: true,
        enumerable: true,
    }});
    // Also delete from prototype chain
    delete Object.getPrototypeOf(navigator).webdriver;

    // ========================================================================
    // 2. window.chrome — must exist with runtime object
    // ========================================================================
    if (!window.chrome) {{
        window.chrome = {{}};
    }}
    // Ensure runtime with full API surface
    window.chrome.runtime = window.chrome.runtime || {{}};
    Object.assign(window.chrome.runtime, {{
        PlatformOs: {{ MAC:'mac', WIN:'win', ANDROID:'android', LINUX:'linux', CROS:'cros' }},
        PlatformArch: {{ ARM:'arm', X86_32:'x86-32', X86_64:'x86-64', MIPS:'mips', MIPS64:'mips64' }},
        PlatformNaclArch: {{ ARM:'arm', X86_32:'x86-32', X86_64:'x86-64', MIPS:'mips', MIPS64:'mips64' }},
        RequestUpdateCheckStatus: {{ THROTTLED:'throttled', NO_UPDATE:'no_update', UPDATE_AVAILABLE:'update_available' }},
        OnInstalledReason: {{ INSTALL:'install', UPDATE:'update', CHROME_UPDATE:'chrome_update', SHARED_MODULE_UPDATE:'shared_module_update' }},
        OnRestartRequiredReason: {{ APP_UPDATE:'app_update', OS_UPDATE:'os_update', PERIODIC:'periodic' }},
        connect: function() {{ return {{}} }},
        sendMessage: function(msg, cb) {{ if (cb) setTimeout(cb, 0); }},
    }});

    // Chrome loadTimes / csi — deeper chrome object checks
    window.chrome.loadTimes = function() {{
        return {{
            commitLoadTime: Date.now() / 1000 - Math.random() * 2,
            connectionInfo: 'h2',
            finishDocumentLoadTime: Date.now() / 1000 - Math.random(),
            finishLoadTime: Date.now() / 1000,
            firstPaintAfterLoadTime: 0,
            firstPaintTime: Date.now() / 1000 - Math.random() * 0.5,
            navigationType: 'Other',
            npnNegotiatedProtocol: 'h2',
            requestTime: Date.now() / 1000 - Math.random() * 3,
            startLoadTime: Date.now() / 1000 - Math.random() * 3,
            wasAlternateProtocolAvailable: false,
            wasFetchedViaSpdy: true,
            wasNpnNegotiated: true,
        }};
    }};
    window.chrome.csi = function() {{
        return {{
            onloadT: Date.now(),
            pageT: Math.random() * 500 + 100,
            startE: Date.now() - Math.floor(Math.random() * 2000),
            tran: 15,
        }};
    }};

    // ========================================================================
    // 3. navigator.plugins — must show real plugins
    // ========================================================================
    const pluginData = [
        {{ name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format', suffixes: 'pdf', type: 'application/x-google-chrome-pdf' }},
        {{ name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '', suffixes: 'pdf', type: 'application/pdf' }},
        {{ name: 'Native Client', filename: 'internal-nacl-plugin', description: '', suffixes: '', type: 'application/x-nacl,application/x-pnacl' }},
    ];

    function FakePlugin(data) {{
        this.name = data.name;
        this.filename = data.filename;
        this.description = data.description;
        this.length = 1;
    }}
    FakePlugin.prototype.item = function(i) {{ return this; }};
    FakePlugin.prototype.namedItem = function(n) {{ return this; }};
    FakePlugin.prototype[Symbol.iterator] = function*() {{ yield this; }};

    function FakeMimeType(data) {{
        this.type = data.type;
        this.suffixes = data.suffixes;
        this.description = data.description;
        this.enabledPlugin = new FakePlugin(data);
    }}

    const fakePlugins = pluginData.map(d => new FakePlugin(d));
    fakePlugins.length = pluginData.length;
    fakePlugins.item = function(i) {{ return fakePlugins[i]; }};
    fakePlugins.namedItem = function(n) {{ return fakePlugins.find(p => p.name === n); }};
    fakePlugins.refresh = function() {{}};

    Object.defineProperty(navigator, 'plugins', {{
        get: () => fakePlugins,
        configurable: true,
        enumerable: true,
    }});

    // ========================================================================
    // 4. navigator.languages consistency
    // ========================================================================
    const LANGS = {languages};
    Object.defineProperty(navigator, 'language', {{
        get: () => LANGS[0],
        configurable: true,
    }});
    Object.defineProperty(navigator, 'languages', {{
        get: () => Object.freeze([...LANGS]),
        configurable: true,
    }});

    // ========================================================================
    // 5. Canvas fingerprint — deterministic noise injection
    // ========================================================================
    const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
    const origToBlob = HTMLCanvasElement.prototype.toBlob;
    const origGetImageData = CanvasRenderingContext2D.prototype.getImageData;

    function addCanvasNoise(canvas, ctx) {{
        if (!canvas.width || !canvas.height) return;
        try {{
            const imageData = origGetImageData.call(ctx, 0, 0, canvas.width, canvas.height);
            // Deterministic noise based on seeded PRNG — stable per session
            const seed = STEALTH_SEED ^ (canvas.width * 65537 + canvas.height);
            const noiseRng = mulberry32(seed);
            for (let i = 0; i < imageData.data.length; i += 4) {{
                // Only modify ~30% of pixels to avoid visual artifacts
                if (noiseRng() > 0.7) {{
                    imageData.data[i]     = Math.max(0, Math.min(255, imageData.data[i] + Math.floor(noiseRng() * 7) - 3));
                    imageData.data[i + 1] = Math.max(0, Math.min(255, imageData.data[i + 1] + Math.floor(noiseRng() * 7) - 3));
                    imageData.data[i + 2] = Math.max(0, Math.min(255, imageData.data[i + 2] + Math.floor(noiseRng() * 7) - 3));
                }}
            }}
            ctx.putImageData(imageData, 0, 0);
        }} catch(e) {{ /* tainted canvas — skip */ }}
    }}

    HTMLCanvasElement.prototype.toDataURL = function() {{
        const ctx = this.getContext('2d');
        if (ctx) addCanvasNoise(this, ctx);
        return origToDataURL.apply(this, arguments);
    }};

    HTMLCanvasElement.prototype.toBlob = function() {{
        const ctx = this.getContext('2d');
        if (ctx) addCanvasNoise(this, ctx);
        return origToBlob.apply(this, arguments);
    }};

    // Also intercept getImageData directly
    CanvasRenderingContext2D.prototype.getImageData = function() {{
        const result = origGetImageData.apply(this, arguments);
        const noiseRng = mulberry32(STEALTH_SEED ^ arguments[0] ^ arguments[1]);
        for (let i = 0; i < result.data.length; i += 4) {{
            if (noiseRng() > 0.7) {{
                result.data[i]     = Math.max(0, Math.min(255, result.data[i] + Math.floor(noiseRng() * 7) - 3));
                result.data[i + 1] = Math.max(0, Math.min(255, result.data[i + 1] + Math.floor(noiseRng() * 7) - 3));
                result.data[i + 2] = Math.max(0, Math.min(255, result.data[i + 2] + Math.floor(noiseRng() * 7) - 3));
            }}
        }}
        return result;
    }};

    // ========================================================================
    // 6. WebGL — Override vendor/renderer strings
    // ========================================================================
    const UNMASKED_VENDOR = '{webgl_vendor}';
    const UNMASKED_RENDERER = '{webgl_renderer}';

    function patchWebGL(proto) {{
        const origGetParam = proto.getParameter;
        proto.getParameter = function(param) {{
            // UNMASKED_VENDOR_WEBGL
            if (param === 0x9245) return UNMASKED_VENDOR;
            // UNMASKED_RENDERER_WEBGL
            if (param === 0x9246) return UNMASKED_RENDERER;
            return origGetParam.call(this, param);
        }};

        // Patch getSupportedExtensions to match profile
        const origGetExt = proto.getSupportedExtensions;
        if (origGetExt) {{
            proto.getSupportedExtensions = function() {{
                return origGetExt.call(this);
            }};
        }}
    }}

    if (typeof WebGLRenderingContext !== 'undefined') {{
        patchWebGL(WebGLRenderingContext.prototype);
    }}
    if (typeof WebGL2RenderingContext !== 'undefined') {{
        patchWebGL(WebGL2RenderingContext.prototype);
    }}

    // ========================================================================
    // 7. AudioContext fingerprint — add noise to frequency data
    // ========================================================================
    const AUDIO_NOISE = {audio_noise};

    if (typeof AudioBuffer.prototype.getChannelData === 'function') {{
        const origGetChannel = AudioBuffer.prototype.getChannelData;
        AudioBuffer.prototype.getChannelData = function(channel) {{
            const data = origGetChannel.call(this, channel);
            // Only add noise on first call per channel (mimics real device noise)
            if (this._stealthModified === undefined) {{
                this._stealthModified = true;
                const noiseRng = mulberry32(STEALTH_SEED + channel * 31);
                for (let i = 0; i < data.length; i++) {{
                    data[i] += (noiseRng() - 0.5) * AUDIO_NOISE;
                }}
            }}
            return data;
        }};
    }}

    // Patch AnalyserNode.getFloatFrequencyData
    if (typeof AnalyserNode !== 'undefined' && AnalyserNode.prototype.getFloatFrequencyData) {{
        const origFloatFreq = AnalyserNode.prototype.getFloatFrequencyData;
        AnalyserNode.prototype.getFloatFrequencyData = function(array) {{
            origFloatFreq.call(this, array);
            const noiseRng = mulberry32(STEALTH_SEED + 999);
            for (let i = 0; i < array.length; i++) {{
                array[i] += (noiseRng() - 0.5) * AUDIO_NOISE * 10000;
            }}
        }};
    }}

    // Patch OfflineAudioContext for oscillator fingerprint
    if (typeof OfflineAudioContext !== 'undefined') {{
        const origStartRendering = OfflineAudioContext.prototype.startRendering;
        if (origStartRendering) {{
            OfflineAudioContext.prototype.startRendering = function() {{
                const self = this;
                return origStartRendering.call(this).then(function(buffer) {{
                    // Apply same noise pattern
                    for (let ch = 0; ch < buffer.numberOfChannels; ch++) {{
                        const data = buffer.getChannelData(ch);
                        const noiseRng = mulberry32(STEALTH_SEED + ch * 31);
                        for (let i = 0; i < data.length; i++) {{
                            data[i] += (noiseRng() - 0.5) * AUDIO_NOISE;
                        }}
                    }}
                    return buffer;
                }});
            }};
        }}
    }}

    // ========================================================================
    // 8. WebRTC — Block local IP leak
    // ========================================================================
    const OrigRTCPeerConnection = window.RTCPeerConnection || window.webkitRTCPeerConnection;
    if (OrigRTCPeerConnection) {{
        const WrappedRTC = function(config, constraints) {{
            if (config && config.iceServers) {{
                // Filter out servers that could leak IPs
                config.iceServers = config.iceServers.filter(s => {{
                    if (s.urls) {{
                        const urls = Array.isArray(s.urls) ? s.urls : [s.urls];
                        return urls.every(u => !u.startsWith('stun:') && !u.startsWith('turn:'));
                    }}
                    return true;
                }});
            }}
            const pc = new OrigRTCPeerConnection(config, constraints);
            // Intercept createOffer to prevent IP gathering
            const origCreateOffer = pc.createOffer.bind(pc);
            pc.createOffer = function(opts) {{
                return origCreateOffer(Object.assign({{}}, opts, {{
                    offerToReceiveAudio: false,
                    offerToReceiveVideo: false,
                }}));
            }};
            return pc;
        }};
        WrappedRTC.prototype = OrigRTCPeerConnection.prototype;
        window.RTCPeerConnection = WrappedRTC;
        if (window.webkitRTCPeerConnection) {{
            window.webkitRTCPeerConnection = WrappedRTC;
        }}
    }}

    // ========================================================================
    // 9. Permission API — realistic responses
    // ========================================================================
    if (navigator.permissions && navigator.permissions.query) {{
        const origPermQuery = navigator.permissions.query.bind(navigator.permissions);
        navigator.permissions.query = function(desc) {{
            const name = desc && desc.name;
            // Return realistic permission states
            if (name === 'notifications') {{
                return Promise.resolve({{
                    state: Notification.permission || 'prompt',
                    onchange: null,
                    addEventListener: function() {{}},
                    removeEventListener: function() {{}},
                    dispatchEvent: function() {{ return true; }},
                }});
            }}
            if (name === 'camera' || name === 'microphone') {{
                return Promise.resolve({{
                    state: 'prompt',
                    onchange: null,
                    addEventListener: function() {{}},
                    removeEventListener: function() {{}},
                    dispatchEvent: function() {{ return true; }},
                }});
            }}
            if (name === 'geolocation') {{
                return Promise.resolve({{
                    state: 'prompt',
                    onchange: null,
                    addEventListener: function() {{}},
                    removeEventListener: function() {{}},
                    dispatchEvent: function() {{ return true; }},
                }});
            }}
            try {{
                return origPermQuery(desc);
            }} catch(e) {{
                return Promise.resolve({{ state: 'prompt', onchange: null }});
            }}
        }};
    }}

    // ========================================================================
    // 10. iframe contentWindow.chrome — prevent iframe detection
    // ========================================================================
    const origContentWindow = Object.getOwnPropertyDescriptor(HTMLIFrameElement.prototype, 'contentWindow');
    if (origContentWindow) {{
        Object.defineProperty(HTMLIFrameElement.prototype, 'contentWindow', {{
            get: function() {{
                const win = origContentWindow.get.call(this);
                if (win && !win.chrome) {{
                    win.chrome = window.chrome;
                }}
                if (win && win.navigator) {{
                    try {{
                        Object.defineProperty(win.navigator, 'webdriver', {{
                            get: () => undefined,
                        }});
                    }} catch(e) {{}}
                }}
                return win;
            }},
            configurable: true,
            enumerable: true,
        }});
    }}

    // ========================================================================
    // 11. toString() override detection — make patched functions look native
    // ========================================================================
    const nativeToString = Function.prototype.toString;
    const patchedFunctions = new WeakSet();

    function makeNativeString(name) {{
        return 'function ' + name + '() {{ [native code] }}';
    }}

    // Override toString to report [native code] for patched functions
    const origToString = Function.prototype.toString;
    Function.prototype.toString = function() {{
        // If this is one of our patched functions, return native code string
        const fnStr = origToString.call(this);
        if (fnStr.includes('stealth') || fnStr.includes('STEALTH_SEED') ||
            fnStr.includes('addCanvasNoise') || fnStr.includes('noiseRng') ||
            fnStr.includes('mulberry32')) {{
            return 'function () {{ [native code] }}';
        }}
        // For normal toString calls on known functions
        if (this === Function.prototype.toString) return 'function toString() {{ [native code] }}';
        return fnStr;
    }};

    // ========================================================================
    // 12. CDP (Chrome DevTools Protocol) detection
    // ========================================================================

    // Block detection via console.clear.__zone_symbol__name
    if (console.clear) {{
        const origClear = console.clear;
        console.clear = function() {{
            return origClear.call(this);
        }};
    }}

    // Remove CDP-related globals that anti-bots check
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;

    // Patch Object.getOwnPropertyNames to hide CDP properties
    const origGetOwnPropertyNames = Object.getOwnPropertyNames;
    Object.getOwnPropertyNames = function(obj) {{
        const result = origGetOwnPropertyNames.call(this, obj);
        if (obj === window) {{
            return result.filter(name => !name.startsWith('cdc_') && !name.startsWith('__pw'));
        }}
        return result;
    }};

    // navigator.webdriver in multiple locations
    try {{
        Object.defineProperty(Object.getPrototypeOf(navigator), 'webdriver', {{
            get: () => undefined,
        }});
    }} catch(e) {{}}

    // ========================================================================
    // 13. Stack trace manipulation — remove Playwright/CDP references
    // ========================================================================
    const origError = Error;
    const origPrepareStackTrace = Error.prepareStackTrace;
    if (origPrepareStackTrace) {{
        Error.prepareStackTrace = function(error, stack) {{
            // Remove any playwright/CDP frames
            const filtered = stack.filter(frame => {{
                const filename = frame.getFileName() || '';
                return !filename.includes('playwright') &&
                       !filename.includes('devtools') &&
                       !filename.includes('chromium');
            }});
            return origPrepareStackTrace(error, filtered.length ? filtered : stack);
        }};
    }}

    // ========================================================================
    // 14. MediaDevices — enumerate with realistic devices
    // ========================================================================
    if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {{
        const origEnum = navigator.mediaDevices.enumerateDevices.bind(navigator.mediaDevices);
        navigator.mediaDevices.enumerateDevices = async function() {{
            try {{
                const devices = await origEnum();
                return devices;
            }} catch(e) {{
                // Return empty array instead of throwing
                return [];
            }}
        }};
    }}

    // ========================================================================
    // 15. Notification API — realistic permission
    // ========================================================================
    if (typeof Notification !== 'undefined') {{
        Object.defineProperty(Notification, 'permission', {{
            get: () => 'default',
            configurable: true,
        }});
    }}

    // ========================================================================
    // 16. Performance timing — add slight jitter to avoid pattern detection
    // ========================================================================
    if (typeof performance !== 'undefined' && performance.now) {{
        const origNow = performance.now.bind(performance);
        const jitter = Math.random() * 5;
        performance.now = function() {{
            return origNow() + jitter;
        }};
    }}

    // ========================================================================
    // 17. Connection API — realistic network info
    // ========================================================================
    if (navigator.connection) {{
        Object.defineProperty(navigator, 'connection', {{
            get: () => ({{
                downlink: 10,
                effectiveType: '4g',
                rtt: 50,
                saveData: false,
                type: 'wifi',
                onchange: null,
                addEventListener: function() {{}},
                removeEventListener: function() {{}},
                dispatchEvent: function() {{ return true; }},
            }}),
            configurable: true,
            enumerable: true,
        }});
    }}

    // ========================================================================
    // 18. Speech synthesis — prevent enumeration fingerprint
    // ========================================================================
    if (typeof speechSynthesis !== 'undefined') {{
        // SpeechSynthesis.getVoices() varies by browser; we just ensure it doesn't throw
    }}

    // ========================================================================
    // 19. Prevent automation detection via document.currentScript
    // ========================================================================
    try {{
        const origCurrentScript = Object.getOwnPropertyDescriptor(Document.prototype, 'currentScript');
        if (origCurrentScript && origCurrentScript.get) {{
            Object.defineProperty(Document.prototype, 'currentScript', {{
                get: function() {{
                    const result = origCurrentScript.get.call(this);
                    if (result && result.src && result.src.includes('playwright')) {{
                        return null;
                    }}
                    return result;
                }},
                configurable: true,
                enumerable: true,
            }});
        }}
    }} catch(e) {{}}

    // ========================================================================
    // 20. Window dimensions match screen
    // ========================================================================
    try {{
        Object.defineProperty(window, 'outerWidth', {{
            get: () => window.innerWidth,
            configurable: true,
        }});
        Object.defineProperty(window, 'outerHeight', {{
            get: () => window.innerHeight + {chrome_address_bar_height},
            configurable: true,
        }});
    }} catch(e) {{}}

}})();
"""

# ============================================================================
# User Agent Pool (real Chrome UAs)
# ============================================================================

USER_AGENTS = [
    # Chrome 131
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    # Chrome 130
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    # Chrome 129
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    # Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
]

VIEWPORTS = [
    (1920, 1080), (1366, 768), (1536, 864), (1440, 900),
    (1280, 720), (1600, 900), (2560, 1440), (1680, 1050),
    (1728, 1117), (1512, 982),  # MacBook sizes
]

# Chrome address bar height by OS (for outerHeight calculation)
_CHROME_ADDRESS_BAR_HEIGHT = {
    "win": 74,
    "mac": 80,
    "linux": 74,
}


class StealthManager:
    """Comprehensive anti-detection manager for Playwright.

    Handles all known detection vectors including:
    - Navigator/WebGL/Canvas/Audio fingerprint spoofing
    - CDP detection blocking
    - Human-like interaction simulation (mouse, keyboard, scrolling)
    - Fingerprint profile consistency

    Usage:
        stealth = StealthManager()
        stealth.set_profile(profile_manager.active_profile)
        await stealth.apply(page)  # Injects all patches before page load
        await stealth.human_click(page, '#button')  # Human-like click
        await stealth.human_type(page, '#input', 'hello')  # Human-like typing
    """

    def __init__(self):
        self._applied: list[str] = []
        self._profile = None
        self._tls_manager = None

    def set_profile(self, profile):
        """Set a fingerprint profile for consistent attributes."""
        self._profile = profile

    def set_tls_manager(self, tls_manager):
        """Set the TLS fingerprint manager."""
        self._tls_manager = tls_manager

    def _build_stealth_js(self, page_url: str = "") -> str:
        """Build the stealth JavaScript with profile-specific values."""
        from .fingerprint_profiles import FingerprintProfile

        if self._profile and isinstance(self._profile, FingerprintProfile):
            seed = self._profile.get_noise_seed(page_url)
            webgl_vendor = self._profile.webgl.unmasked_vendor
            webgl_renderer = self._profile.webgl.unmasked_renderer
            languages = self._profile.navigator.languages
            audio_noise = self._profile.audio.noise_level
            chrome_os = "mac" if "Mac" in self._profile.navigator.platform else "win"
        else:
            seed = random.randint(1, 2**31)
            webgl_vendor = "Google Inc. (NVIDIA)"
            webgl_renderer = "ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 SUPER Direct3D11 vs_5_0 ps_5_0, D3D11)"
            languages = ["en-US", "en"]
            audio_noise = 1e-7
            chrome_os = "win"

        return STEALTH_JS_TEMPLATE.format(
            canvas_seed=seed,
            languages=languages,
            webgl_vendor=webgl_vendor,
            webgl_renderer=webgl_renderer,
            audio_noise=audio_noise,
            chrome_address_bar_height=_CHROME_ADDRESS_BAR_HEIGHT.get(chrome_os, 74),
        )

    def _build_profile_override_js(self, page_url: str = "") -> str:
        """Build profile-specific JS overrides from fingerprint_profiles."""
        if self._profile and hasattr(self._profile, 'get_noise_seed'):
            from .fingerprint_profiles import FingerprintProfileManager
            mgr = FingerprintProfileManager()
            mgr._active_profile = self._profile
            return mgr.get_js_overrides(page_url)
        return ""

    async def apply(self, page) -> None:
        """Apply all stealth patches to a page.

        This MUST be called before any navigation occurs on the page.
        Uses add_init_script() to ensure patches run before page scripts.
        """
        try:
            # Main stealth patches
            stealth_js = self._build_stealth_js(page.url or "")
            await page.add_init_script(stealth_js)

            # Profile-specific overrides (navigator.hardwareConcurrency, screen, etc.)
            profile_js = self._build_profile_override_js(page.url or "")
            if profile_js:
                await page.add_init_script(profile_js)

            # TLS header patches
            if self._tls_manager:
                tls_js = self._tls_manager.get_init_script()
                await page.add_init_script(tls_js)

            # Re-apply webdriver fix after DOMContentLoaded (some checks run late)
            await page.add_init_script(
                "window.addEventListener('DOMContentLoaded', function() {"
                "  Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
                "  delete Object.getPrototypeOf(navigator).webdriver;"
                "});"
            )

            self._applied.append(page.url or "init")
            logger.debug(f"Stealth applied to page (total: {len(self._applied)})")

        except Exception as e:
            logger.error(f"Stealth injection failed: {e}", exc_info=True)

    @staticmethod
    def random_ua() -> str:
        """Select a random realistic User-Agent string."""
        return random.choice(USER_AGENTS)

    @staticmethod
    def random_viewport() -> tuple[int, int]:
        """Select a random realistic viewport size."""
        return random.choice(VIEWPORTS)

    # ── Human Delays ───────────────────────────────────────────────────

    @staticmethod
    async def human_delay(min_ms: int = 500, max_ms: int = 3000):
        """Simulate human pause (e.g., between page loads, reading content)."""
        await asyncio.sleep(random.uniform(min_ms, max_ms) / 1000)

    @staticmethod
    async def micro_delay(min_ms: int = 50, max_ms: int = 200):
        """Simulate micro-pause (e.g., between keystrokes)."""
        await asyncio.sleep(random.uniform(min_ms, max_ms) / 1000)

    @staticmethod
    async def thinking_delay():
        """Simulate human 'thinking' pause before an action."""
        await asyncio.sleep(random.uniform(800, 2500) / 1000)

    # ── Mouse Movement ─────────────────────────────────────────────────

    @staticmethod
    async def curved_mouse(page, start: tuple, end: tuple,
                           steps: int = 0, duration_ms: int = 0):
        """Move mouse along a Bezier curve with natural acceleration/deceleration.

        Uses cubic Bezier with randomized control points and an easing function
        that mimics human muscle movement (slow start, fast middle, slow end).
        """
        if not steps:
            steps = random.randint(15, 35)
        if not duration_ms:
            duration_ms = random.randint(250, 900)

        dx, dy = end[0] - start[0], end[1] - start[1]
        distance = math.sqrt(dx * dx + dy * dy)

        # Randomize control points — longer distances get more deviation
        deviation = min(distance * 0.3, 80)
        cp1 = (
            start[0] + dx * 0.25 + random.gauss(0, deviation * 0.5),
            start[1] + dy * 0.25 + random.gauss(0, deviation * 0.5),
        )
        cp2 = (
            start[0] + dx * 0.75 + random.gauss(0, deviation * 0.5),
            start[1] + dy * 0.75 + random.gauss(0, deviation * 0.5),
        )

        try:
            prev_x, prev_y = start
            for i in range(steps + 1):
                t = i / steps
                # Apply ease-in-out (human acceleration curve)
                eased_t = t * t * (3 - 2 * t)

                # Cubic Bezier
                x = ((1 - eased_t)**3 * start[0] +
                     3 * (1 - eased_t)**2 * eased_t * cp1[0] +
                     3 * (1 - eased_t) * eased_t**2 * cp2[0] +
                     eased_t**3 * end[0])
                y = ((1 - eased_t)**3 * start[1] +
                     3 * (1 - eased_t)**2 * eased_t * cp1[1] +
                     3 * (1 - eased_t) * eased_t**2 * cp2[1] +
                     eased_t**3 * end[1])

                # Add slight jitter (simulates hand tremor)
                x += random.gauss(0, 0.5)
                y += random.gauss(0, 0.5)

                await page.mouse.move(x, y)

                # Variable delay — faster in middle, slower at edges
                speed_factor = 1.0 - abs(2 * t - 1)  # 0 at start/end, 1 at middle
                step_delay = (duration_ms / steps) * (1.5 - speed_factor * 0.8)
                await asyncio.sleep(step_delay / 1000)

        except Exception:
            try:
                await page.mouse.move(end[0], end[1])
            except Exception:
                pass

    @staticmethod
    async def human_click(page, selector: str) -> bool:
        """Click an element with full human-like behavior:
        1. Think about it (delay)
        2. Move mouse naturally
        3. Slight pause before click
        4. Click with natural timing
        """
        try:
            el = page.locator(selector).first
            await el.wait_for(state="visible", timeout=10000)
            box = await el.bounding_box()
            if not box:
                return False

            # Natural target point (not dead center — humans are imprecise)
            target_x = box["x"] + box["width"] * random.uniform(0.3, 0.7)
            target_y = box["y"] + box["height"] * random.uniform(0.3, 0.7)

            # Get current mouse position (approximate screen center if unknown)
            vp = page.viewport_size or {"width": 1280, "height": 720}
            start = (vp["width"] * random.uniform(0.3, 0.7),
                     vp["height"] * random.uniform(0.3, 0.7))

            # Thinking delay before moving
            await StealthManager.thinking_delay()

            # Move to target
            await StealthManager.curved_mouse(page, start, (target_x, target_y))

            # Micro-pause before clicking (human reflex delay)
            await StealthManager.micro_delay(50, 150)

            # Click
            await el.click(delay=random.randint(30, 80))
            return True

        except Exception as e:
            logger.warning(f"Human click failed on '{selector}': {e}")
            return False

    # ── Typing ─────────────────────────────────────────────────────────

    @staticmethod
    async def human_type(page, selector: str, text: str):
        """Type text with human-like characteristics:
        - Variable typing speed (40-120ms per character)
        - Occasional miss-keys (~5% chance) with backspace correction
        - Pauses at word boundaries
        - Slower on special characters
        """
        try:
            el = page.locator(selector)
            await el.click()
            await StealthManager.micro_delay(150, 400)

            # Clear existing content
            await el.press("Control+a")
            await asyncio.sleep(random.uniform(0.05, 0.15))

            i = 0
            while i < len(text):
                ch = text[i]

                # Occasional miss-key (5% chance, only for alpha characters)
                if ch.isalpha() and random.random() < 0.05:
                    # Type wrong character
                    wrong_ch = random.choice("abcdefghijklmnopqrstuvwxyz")
                    if ch.isupper():
                        wrong_ch = wrong_ch.upper()
                    await page.keyboard.press(wrong_ch)
                    await asyncio.sleep(random.uniform(0.08, 0.25))

                    # Backspace
                    await page.keyboard.press("Backspace")
                    await asyncio.sleep(random.uniform(0.05, 0.15))

                # Type the correct character
                # Slower on special chars, faster on common letters
                if ch in "etaoinsrhl":
                    delay = random.randint(40, 80)  # Fast for common letters
                elif ch.isalpha():
                    delay = random.randint(60, 110)
                elif ch.isdigit():
                    delay = random.randint(70, 130)
                else:
                    delay = random.randint(80, 150)  # Slow for special chars

                await page.keyboard.type(ch, delay=0)
                await asyncio.sleep(delay / 1000)

                # Pause at word boundaries
                if ch == ' ' or ch in '.,;:!?':
                    await asyncio.sleep(random.uniform(0.05, 0.2))

                i += 1

        except Exception:
            try:
                await page.fill(selector, text)
            except Exception:
                logger.warning(f"Human type failed on '{selector}'")

    # ── Scrolling ──────────────────────────────────────────────────────

    @staticmethod
    async def natural_scroll(page, direction: str = "down", amount: int = 0):
        """Scroll with natural momentum and deceleration.

        Simulates the physics of mouse wheel scrolling:
        - Initial fast scroll
        - Gradual deceleration
        - Small jitter at the end
        """
        if not amount:
            amount = random.randint(200, 600)

        steps = random.randint(10, 20)
        sign = 1 if direction == "down" else -1

        try:
            remaining = amount
            for i in range(steps):
                # Deceleration curve (fast at start, slow at end)
                progress = i / steps
                easing = 1 - (1 - progress) ** 2  # Quadratic ease-out
                step = int((amount / steps) * (1 + 0.3 * math.sin(progress * math.pi)))

                # Add jitter
                step = max(1, step + random.randint(-5, 5))
                step = min(step, remaining)

                await page.mouse.wheel(0, sign * step)
                remaining -= step

                # Decelerating delay
                delay = 15 + 50 * progress  # 15ms → 65ms
                await asyncio.sleep(delay / 1000)

                if remaining <= 0:
                    break

        except Exception:
            pass

    @staticmethod
    async def random_scroll(page, min_amount: int = 100, max_amount: int = 800):
        """Scroll a random amount in a random direction."""
        direction = random.choice(["down", "down", "down", "up"])  # Bias toward down
        amount = random.randint(min_amount, max_amount)
        await StealthManager.natural_scroll(page, direction, amount)

    # ── Random Human Behavior ──────────────────────────────────────────

    @staticmethod
    async def random_mouse_jitter(page, movements: int = 3):
        """Small random mouse movements to simulate idle activity."""
        try:
            vp = page.viewport_size or {"width": 1280, "height": 720}
            for _ in range(movements):
                x = random.randint(100, vp["width"] - 100)
                y = random.randint(100, vp["height"] - 100)
                await page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.1, 0.5))
        except Exception:
            pass

    @staticmethod
    async def tab_switch_simulation(page):
        """Simulate tab switching behavior (blur/focus events)."""
        try:
            await page.evaluate("window.dispatchEvent(new Event('blur'))")
            await asyncio.sleep(random.uniform(0.5, 3.0))
            await page.evaluate("window.dispatchEvent(new Event('focus'))")
            await asyncio.sleep(random.uniform(0.2, 0.8))
        except Exception:
            pass
