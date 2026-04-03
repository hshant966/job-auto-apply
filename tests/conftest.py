"""Shared test fixtures and mocks for the test suite."""

import sys
from unittest.mock import MagicMock

# Mock external dependencies that may not be installed in test env.
# These must be mocked BEFORE any src imports occur.

# --- Playwright (browser automation) ---
_pw_api = MagicMock()
for mod_name in ["playwright", "playwright.async_api", "playwright.sync_api"]:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = _pw_api if mod_name == "playwright" else MagicMock()

# --- Pydantic (data validation) ---
# Must provide BaseModel as a real class so 'class Foo(BaseModel)' works.
import types as _types

_pydantic_module = _types.ModuleType("pydantic")
_pydantic_module.BaseModel = type("BaseModel", (), {"__init__": lambda self, **kw: None})
_pydantic_module.Field = lambda *a, **kw: None
_pydantic_module.ValidationError = type("ValidationError", (Exception,), {})
_pydantic_module.field_validator = lambda *a, **kw: (lambda fn: fn)
_pydantic_module.model_validator = lambda *a, **kw: (lambda fn: fn)
_pydantic_module.validator = lambda *a, **kw: (lambda fn: fn)
_pydantic_module.root_validator = lambda *a, **kw: (lambda fn: fn)
sys.modules.setdefault("pydantic", _pydantic_module)

# --- FastAPI ---
import importlib

_fastapi_module = _types.ModuleType("fastapi")

class _FakeFastAPI:
    def __init__(self, *a, **kw):
        self.routes = []
    def mount(self, *a, **kw): pass
    def include_router(self, router, *a, **kw):
        if hasattr(router, "routes"):
            self.routes.extend(router.routes)

class _FakeAPIRouter:
    def __init__(self, *a, **kw):
        self.routes = []
    def get(self, path, *a, **kw):
        def decorator(fn):
            self.routes.append(type("Route", (), {"path": path, "method": "GET"})())
            return fn
        return decorator
    def post(self, path, *a, **kw):
        def decorator(fn):
            self.routes.append(type("Route", (), {"path": path, "method": "POST"})())
            return fn
        return decorator

_fastapi_module.FastAPI = _FakeFastAPI
_fastapi_module.APIRouter = _FakeAPIRouter
_fastapi_module.HTTPException = type("HTTPException", (Exception,), {"__init__": lambda self, status_code=500, detail="": None})
_fastapi_module.File = lambda *a, **kw: None
_fastapi_module.UploadFile = MagicMock
# Catch-all for any other fastapi names (Request, Depends, Form, etc.)
_fastapi_module.__getattr__ = lambda name: MagicMock(name=name)
sys.modules["fastapi"] = _fastapi_module

# Mock all fastapi submodules (responses, staticfiles, templating, etc.)
for _sub in ["responses", "staticfiles", "templating", "middleware", "middleware.cors",
             "security", "encoders", "concurrency", "testclient"]:
    _sub_mod = _types.ModuleType(f"fastapi.{_sub}")
    _sub_mod.__getattr__ = lambda name: MagicMock(name=name)
    sys.modules[f"fastapi.{_sub}"] = _sub_mod

# --- Feedparser & httpx ---
sys.modules.setdefault("feedparser", MagicMock())
sys.modules.setdefault("httpx", MagicMock())

# --- Jinja2 ---
sys.modules.setdefault("jinja2", MagicMock())
