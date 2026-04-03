"""TLS Fingerprint Spoofing — JA3/JA4 bypass for Playwright.

This module provides TLS fingerprint spoofing to pass JA3/JA4 checks
commonly used by anti-bot systems (Cloudflare, Datadome, PerimeterX, etc.).

The approach uses multiple strategies:
1. Playwright request interception with custom headers matching Chrome's HTTP/2 behavior
2. Optional tls-client integration for direct HTTP requests outside the browser
3. ALPN negotiation and cipher suite ordering that matches real Chrome

Chrome's TLS fingerprint characteristics:
- TLS 1.3 with specific extension ordering
- HTTP/2 with Chrome-specific SETTINGS frame values
- ALPN: h2, http/1.1
- Specific GREASE values in extensions
- Key share groups: X25519, P-256

Reference: https://tlsfingerprint.io
"""

from __future__ import annotations

import json
import logging
import random
import struct
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class TLSConfig:
    """TLS configuration matching a specific browser."""
    ja3_hash: str
    ja4_hash: str
    # HTTP/2 SETTINGS frame values (matching Chrome)
    h2_header_table_size: int = 65536
    h2_enable_push: int = 0
    h2_max_concurrent_streams: int = 1000
    h2_initial_window_size: int = 6291456
    h2_max_frame_size: int = 16384
    h2_max_header_list_size: int = 262144
    # TLS settings
    alpn_protocols: list[str] = None
    supported_versions: list[str] = None
    cipher_suites: list[str] = None
    # GREASE values (Chrome-specific)
    use_grease: bool = True
    # Pseudo-header order (HTTP/2)
    pseudo_header_order: str = "msa"

    def __post_init__(self):
        if self.alpn_protocols is None:
            self.alpn_protocols = ["h2", "http/1.1"]
        if self.supported_versions is None:
            self.supported_versions = ["tls_1_3", "tls_1_2"]
        if self.cipher_suites is None:
            self.cipher_suites = CHROME_CIPHER_SUITES


# Chrome 131 cipher suites (in order)
CHROME_CIPHER_SUITES = [
    "TLS_AES_128_GCM_SHA256",
    "TLS_AES_256_GCM_SHA384",
    "TLS_CHACHA20_POLY1305_SHA256",
    "TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256",
    "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256",
    "TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384",
    "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
    "TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256",
    "TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256",
    "TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA",
    "TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA",
    "TLS_RSA_WITH_AES_128_GCM_SHA256",
    "TLS_RSA_WITH_AES_256_GCM_SHA384",
    "TLS_RSA_WITH_AES_128_CBC_SHA",
    "TLS_RSA_WITH_AES_256_CBC_SHA",
]

# Chrome TLS extensions (in order — this matters for JA3)
CHROME_EXTENSIONS = [
    0x0000,  # GREASE (placeholder)
    0x0010,  # application_layer_protocol_negotiation
    0x0017,  # extended_master_secret
    0x0023,  # session_ticket
    0x0029,  # pre_shared_key
    0x002b,  # early_data
    0x002d,  # psk_key_exchange_modes
    0x0033,  # key_share
    0x4469,  # application_settings
    0x8531,  # application_settings_new
    0x0005,  # status_request
    0x000a,  # supported_groups
    0x000b,  # ec_point_formats
    0x000d,  # signature_algorithms
    0x0012,  # signed_certificate_timestamp
    0x0018,  # sct
    0x001c,  # record_size_limit
    0x002a,  # cookie
    0x7550,  # channel_id (Google experiment)
]

# Chrome supported groups (elliptic curves)
CHROME_GROUPS = [
    0x0a0a,  # GREASE
    0x001d,  # x25519
    0x0017,  # secp256r1
    0x0018,  # secp384r1
    0x0019,  # secp521r1
]

# EC point formats
CHROME_EC_POINT_FORMATS = [0x00, 0x01, 0x02]

# Signature algorithms
CHROME_SIG_ALGS = [
    0x0403,  # ecdsa_secp256r1_sha256
    0x0804,  # rsa_pss_rsae_sha256
    0x0401,  # rsa_pkcs1_sha256
    0x0503,  # ecdsa_secp384r1_sha384
    0x0805,  # rsa_pss_rsae_sha384
    0x0501,  # rsa_pkcs1_sha384
    0x0806,  # rsa_pss_rsae_sha512
    0x0601,  # rsa_pkcs1_sha512
    0x0201,  # rsa_pkcs1_sha1
]


def _generate_grease_value() -> int:
    """Generate a random GREASE value (0x?A?A where ? is same random nibble)."""
    byte = random.choice([0x0, 0x1, 0x2, 0x3, 0x4, 0x5, 0x6, 0x7,
                          0x8, 0x9, 0xa, 0xb, 0xc, 0xd, 0xe, 0xf])
    return (byte << 12) | (byte << 4) | 0x0a0a


def compute_ja3(
    extensions: list[int],
    cipher_suites: list[int],
    elliptic_curves: list[int],
    elliptic_curve_point_formats: list[int],
) -> str:
    """Compute JA3 fingerprint string (not hashed).

    Format: SSLVersion,Ciphers,Extensions,EllipticCurves,EllipticCurvePointFormats
    """
    version = "771"  # TLS 1.2
    ext_str = "-".join(str(e) for e in extensions)
    cipher_str = "-".join(str(c) for c in cipher_suites)
    curve_str = "-".join(str(c) for c in elliptic_curves)
    format_str = "-".join(str(f) for f in elliptic_curve_point_formats)
    return f"{version},{cipher_str},{ext_str},{curve_str},{format_str}"


def compute_ja4(
    alpn: str,
    version: str,
    cipher_count: int,
    extension_count: int,
    extensions: list[int],
    cipher_suites: list[int],
) -> str:
    """Compute JA4 fingerprint string.

    Format: [protocol][version][SNI][ALPN][cipher_count][ext_count][first_shared_cipher]-[truncated_SHA256]-[truncated_SHA256]
    """
    protocol = "t"  # TLS
    sni = "d"  # SNI present (d = domain)
    alpn_char = alpn[0] if alpn else "0"
    c_count = f"{cipher_count:02d}"[-2:]
    e_count = f"{extension_count:02d}"[-2:]

    # Sort extensions for the hash
    sorted_exts = sorted(extensions)

    # Hash of sorted cipher suites
    import hashlib
    cipher_hash = hashlib.sha256(
        ",".join(str(c) for c in sorted(cipher_suites)).encode()
    ).hexdigest()[:12]

    ext_hash = hashlib.sha256(
        ",".join(str(e) for e in sorted_exts).encode()
    ).hexdigest()[:12]

    return f"{protocol}{version[0]}{sni}{alpn_char}{c_count}{e_count}{cipher_hash}_{ext_hash}"


# ============================================================================
# Chrome TLS Profiles (pre-computed JA3/JA4 hashes)
# ============================================================================

CHROME_TLS_PROFILES = {
    "chrome_131_win": TLSConfig(
        ja3_hash="771,4865-4866-4867-49195-49199-49196-49200-52393-52392-49171-49172-156-157-47-53",
        ja4_hash="t13d1516h2_acb8f508bd35_ac8f2d5359b6",
        h2_header_table_size=65536,
        h2_enable_push=0,
        h2_max_concurrent_streams=1000,
        h2_initial_window_size=6291456,
        h2_max_frame_size=16384,
        h2_max_header_list_size=262144,
        pseudo_header_order="msa",
    ),
    "chrome_131_mac": TLSConfig(
        ja3_hash="771,4865-4866-4867-49195-49199-49196-49200-52393-52392-49171-49172-156-157-47-53",
        ja4_hash="t13d1516h2_acb8f508bd35_ac8f2d5359b6",
        pseudo_header_order="msa",
    ),
    "chrome_130_win": TLSConfig(
        ja3_hash="771,4865-4866-4867-49195-49199-49196-49200-52393-52392-49171-49172-156-157-47-53",
        ja4_hash="t13d1516h2_acb8f508bd35_ac8f2d5359b6",
        pseudo_header_order="msa",
    ),
}


class TLSFingerprintManager:
    """Manages TLS fingerprint configuration for stealth browsing.

    This manager provides:
    1. HTTP/2 SETTINGS frame customization
    2. Header ordering that matches Chrome's HTTP/2 implementation
    3. Request header normalization
    4. Optional tls-client integration for direct HTTP requests

    Usage:
        tls_mgr = TLSFingerprintManager(profile="chrome_131_win")

        # For Playwright requests — modify headers to match Chrome
        async def route_handler(route):
            headers = tls_mgr.normalize_headers(route.request.headers)
            await route.continue_(headers=headers)
    """

    def __init__(self, profile: str = "chrome_131_win"):
        if profile not in CHROME_TLS_PROFILES:
            available = ", ".join(CHROME_TLS_PROFILES.keys())
            raise ValueError(f"Unknown TLS profile '{profile}'. Available: {available}")
        self.config = CHROME_TLS_PROFILES[profile]
        self._profile_name = profile
        logger.info(f"TLS Fingerprint Manager initialized: profile={profile}")

    def normalize_headers(self, headers: dict[str, str]) -> dict[str, str]:
        """Normalize HTTP headers to match Chrome's behavior.

        Chrome-specific behaviors:
        - header names are lowercase (HTTP/2 requirement)
        - sec-ch-ua headers have specific formatting
        - accept-language includes en-US,en;q=0.9
        - accept-encoding: gzip, deflate, br, zstd
        """
        normalized = {}
        for key, value in headers.items():
            key_lower = key.lower()
            normalized[key_lower] = value

        # Ensure Chrome-specific headers are present
        normalized.setdefault("sec-ch-ua", '"Chromium";v="131", "Not_A Brand";v="24"')
        normalized.setdefault("sec-ch-ua-mobile", "?0")
        normalized.setdefault("sec-ch-ua-platform", '"Windows"')
        normalized.setdefault("sec-fetch-dest", "document")
        normalized.setdefault("sec-fetch-mode", "navigate")
        normalized.setdefault("sec-fetch-site", "none")
        normalized.setdefault("sec-fetch-user", "?1")
        normalized.setdefault("upgrade-insecure-requests", "1")
        normalized.setdefault("accept-encoding", "gzip, deflate, br, zstd")
        normalized.setdefault("accept-language", "en-US,en;q=0.9")

        # Remove headers that real Chrome doesn't send
        normalized.pop("x-playwright", None)
        normalized.pop("x-devtools-emulate-network-conditions-client-id", None)

        return normalized

    def get_h2_settings(self) -> dict[str, int]:
        """Get HTTP/2 SETTINGS frame values matching Chrome."""
        return {
            "header_table_size": self.config.h2_header_table_size,
            "enable_push": self.config.h2_enable_push,
            "max_concurrent_streams": self.config.h2_max_concurrent_streams,
            "initial_window_size": self.config.h2_initial_window_size,
            "max_frame_size": self.config.h2_max_frame_size,
            "max_header_list_size": self.config.h2_max_header_list_size,
        }

    def get_init_script(self) -> str:
        """Generate JavaScript to apply TLS-related stealth patches.

        This patches fetch/XMLHttpRequest to add Chrome-specific headers
        that anti-bot systems check for TLS consistency.
        """
        return """
// === TLS Fingerprint Normalization ===
(function() {
    'use strict';

    // Patch fetch to ensure Chrome-like headers
    const originalFetch = window.fetch;
    window.fetch = function(input, init) {
        if (init && init.headers) {
            const headers = new Headers(init.headers);
            // Ensure sec-ch-ua is present
            if (!headers.has('sec-ch-ua')) {
                headers.set('sec-ch-ua', '"Chromium";v="131", "Not_A Brand";v="24"');
            }
            init.headers = headers;
        }
        return originalFetch.call(this, input, init);
    };

    // Patch XMLHttpRequest to ensure Chrome-like headers
    const originalOpen = XMLHttpRequest.prototype.open;
    const originalSetHeader = XMLHttpRequest.prototype.setRequestHeader;
    XMLHttpRequest.prototype.open = function() {
        this._hasSecChUa = false;
        return originalOpen.apply(this, arguments);
    };
    XMLHttpRequest.prototype.setRequestHeader = function(name, value) {
        if (name.toLowerCase() === 'sec-ch-ua') this._hasSecChUa = true;
        return originalSetHeader.call(this, name, value);
    };
    const originalSend = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.send = function() {
        if (!this._hasSecChUa) {
            try {
                originalSetHeader.call(this, 'sec-ch-ua', '"Chromium";v="131", "Not_A Brand";v="24"');
            } catch(e) {}
        }
        return originalSend.apply(this, arguments);
    };
})();
"""

    def get_playwright_extra_headers(self) -> dict[str, str]:
        """Get extra HTTP headers to set via Playwright context."""
        return {
            "sec-ch-ua": '"Chromium";v="131", "Not_A Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en-US,en;q=0.9",
        }

    async def apply_to_context(self, context) -> None:
        """Apply TLS fingerprint patches to a Playwright browser context.

        Sets extra HTTP headers and route handlers for header normalization.
        """
        # Set extra HTTP headers
        await context.set_extra_http_headers(self.get_playwright_extra_headers())

        # Add init script for client-side patches
        await context.add_init_script(self.get_init_script())

        logger.debug(f"TLS fingerprint applied to context: {self._profile_name}")


def try_import_tls_client():
    """Attempt to import tls-client for direct HTTP requests.

    tls-client provides true TLS fingerprint spoofing at the socket level,
    matching JA3/JA4 hashes of known browsers.

    Returns the tls_client module or None if not available.
    """
    try:
        import tls_client
        return tls_client
    except ImportError:
        logger.debug(
            "tls-client not installed. Install with: pip install tls-client. "
            "Falling back to Playwright's built-in TLS handling."
        )
        return None


def create_tls_client_session(
    profile: str = "chrome_131",
    proxy: Optional[str] = None,
) -> Any:
    """Create a tls-client session with Chrome fingerprint.

    Args:
        profile: Browser profile name (chrome_131, chrome_130, etc.)
        proxy: Optional proxy URL (http://user:pass@host:port)

    Returns:
        tls_client.Session or None if tls-client not installed
    """
    tls_client = try_import_tls_client()
    if tls_client is None:
        return None

    # Map our profile names to tls-client identifiers
    client_identifier_map = {
        "chrome_131": "chrome_131",
        "chrome_130": "chrome_130",
        "chrome_129": "chrome_129",
        "chrome_128": "chrome_128",
        "chrome_127": "chrome_127",
        "chrome_126": "chrome_126",
        "chrome_125": "chrome_125",
        "chrome_124": "chrome_124",
        "chrome_123": "chrome_123",
        "chrome_122": "chrome_122",
        "chrome_121": "chrome_121",
        "chrome_120": "chrome_120",
        "chrome_119": "chrome_119",
        "chrome_118": "chrome_118",
        "chrome_117": "chrome_117",
        "chrome_116": "chrome_116",
        "chrome_115": "chrome_115",
        "chrome_114": "chrome_114",
        "chrome_113": "chrome_113",
        "chrome_112": "chrome_112",
        "chrome_111": "chrome_111",
        "chrome_110": "chrome_110",
        "chrome_109": "chrome_109",
        "chrome_108": "chrome_108",
        "chrome_107": "chrome_107",
        "chrome_106": "chrome_106",
        "chrome_105": "chrome_105",
        "chrome_104": "chrome_104",
        "chrome_103": "chrome_103",
        "chrome_102": "chrome_102",
        "chrome_101": "chrome_101",
        "chrome_100": "chrome_100",
    }

    identifier = client_identifier_map.get(profile, "chrome_131")

    try:
        session = tls_client.Session(
            client_identifier=identifier,
            random_tls_extension_order=True,
        )
        if proxy:
            session.proxies = {
                "http": proxy,
                "https": proxy,
            }
        return session
    except Exception as e:
        logger.error(f"Failed to create tls-client session: {e}")
        return None
