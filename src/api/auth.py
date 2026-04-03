"""Authentication & session management API."""
from __future__ import annotations
import logging
import os
import secrets
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

_sessions: dict[str, dict] = {}

# Generate a random admin password if not set via env
_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
if not _ADMIN_PASSWORD:
    _ADMIN_PASSWORD = secrets.token_hex(8)
    logger.warning(
        "ADMIN_PASSWORD env var not set — generated a random password. "
        "Check startup log for credentials."
    )
    print(f"[STARTUP] Generated ADMIN_PASSWORD: {_ADMIN_PASSWORD}")


class LoginRequest(BaseModel):
    username: str = "admin"
    password: str = ""

class LoginResponse(BaseModel):
    token: str
    expires_in: int = 86400


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    """Authenticate and receive a session token."""
    if req.password != _ADMIN_PASSWORD:
        raise HTTPException(401, "Invalid credentials")
    token = secrets.token_hex(32)
    _sessions[token] = {"username": req.username, "active": True}
    return LoginResponse(token=token)

@router.post("/logout")
async def logout(token: str = ""):
    _sessions.pop(token, None)
    return {"ok": True}

@router.get("/check")
async def check_auth(token: str = ""):
    if token in _sessions:
        return {"authenticated": True, "username": _sessions[token]["username"]}
    return {"authenticated": False}


# ── Auth middleware ────────────────────────────────────────────────

_EXEMPT_PREFIXES = ("/api/auth/", "/static/", "/docs", "/openapi.json", "/redoc")


async def auth_middleware(request: Request, call_next):
    """Require authentication on all API routes except login, static, and docs."""
    path = request.url.path
    if any(path.startswith(p) for p in _EXEMPT_PREFIXES):
        return await call_next(request)

    # Check token from header, query param, or cookie
    token = (
        request.headers.get("Authorization", "").removeprefix("Bearer ")
        or request.query_params.get("token", "")
        or request.cookies.get("token", "")
    )
    if not token or token not in _sessions:
        return JSONResponse(
            status_code=401,
            content={"detail": "Authentication required. POST /api/auth/login first."},
        )
    return await call_next(request)


def register_auth_middleware(app):
    """Attach the auth middleware to a FastAPI app."""
    @app.middleware("http")
    async def _auth(request: Request, call_next):
        return await auth_middleware(request, call_next)
