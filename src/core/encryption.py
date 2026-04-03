"""AES encryption utilities for sensitive data at rest.

Uses PBKDF2 for key derivation and AES-256-GCM for authenticated encryption.
"""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

_SALT_LEN = 16
_NONCE_LEN = 12
_KEY_LEN = 32
_KDF_ITERATIONS = 480_000


def derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=_KEY_LEN,
        salt=salt,
        iterations=_KDF_ITERATIONS,
    )
    return kdf.derive(password.encode("utf-8"))


def encrypt(plaintext: str, password: str) -> str:
    if not plaintext:
        return ""
    salt = secrets.token_bytes(_SALT_LEN)
    key = derive_key(password, salt)
    nonce = secrets.token_bytes(_NONCE_LEN)
    aesgcm = AESGCM(key)
    ct = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    blob = salt + nonce + ct
    return base64.b64encode(blob).decode("ascii")


def decrypt(blob_b64: str, password: str) -> str:
    if not blob_b64:
        return ""
    try:
        blob = base64.b64decode(blob_b64, validate=True)
    except Exception as exc:
        raise ValueError("Invalid base64 blob") from exc
    if len(blob) < _SALT_LEN + _NONCE_LEN + 1:
        raise ValueError("Blob too short")
    salt = blob[:_SALT_LEN]
    nonce = blob[_SALT_LEN:_SALT_LEN + _NONCE_LEN]
    ct = blob[_SALT_LEN + _NONCE_LEN:]
    key = derive_key(password, salt)
    aesgcm = AESGCM(key)
    try:
        pt = aesgcm.decrypt(nonce, ct, None)
    except Exception as exc:
        raise ValueError("Decryption failed") from exc
    return pt.decode("utf-8")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.sha256(salt + password.encode("utf-8")).hexdigest()
    return salt.hex() + ":" + digest


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest = stored.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        expected = hashlib.sha256(salt + password.encode("utf-8")).hexdigest()
        return secrets.compare_digest(expected, digest)
    except (ValueError, AttributeError):
        return False
