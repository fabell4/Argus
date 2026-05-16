"""Argus FastAPI application.

Run with:  uvicorn src.api.main:app --host 0.0.0.0 --port 8000

Serves:
- REST API under /api/
- React SPA static files from frontend/dist
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from src import config
from src.api.routes import config as config_router
from src.api.routes import diagnostics, events, snapshots, trigger, devices

_LOG = logging.getLogger(__name__)
_STATIC_DIR = "frontend/dist"
_MAX_REQUEST_BYTES = 1 * 1024 * 1024  # 1 MB


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

class _RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Any) -> Response:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > _MAX_REQUEST_BYTES:
            return Response(content="Request body too large.", status_code=413)
        response: Response = await call_next(request)
        return response


class _SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Any) -> Response:
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    _LOG.info("Argus API starting.")
    yield
    _LOG.info("Argus API shutting down.")


def create_app() -> FastAPI:
    application = FastAPI(
        title="Argus API",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=_lifespan,
    )

    application.add_middleware(_SecurityHeadersMiddleware)
    application.add_middleware(_RequestSizeLimitMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=config.ALLOWED_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["*"],
    )

    # API routers
    application.include_router(snapshots.router, prefix="/api")
    application.include_router(events.router, prefix="/api")
    application.include_router(devices.router, prefix="/api")
    application.include_router(trigger.router, prefix="/api")
    application.include_router(config_router.router, prefix="/api")
    application.include_router(diagnostics.router, prefix="/api")

    # Health endpoint
    @application.get("/api/health", tags=["health"])
    def health() -> dict[str, Any]:
        from src import runtime_config
        return {
            "status": "ok",
            "service": "argus-api",
            "last_poll_at": runtime_config.get_last_poll_at(),
            "next_poll_at": runtime_config.get_next_poll_at(),
            "is_polling": runtime_config.is_running(),
        }

    # Serve React SPA
    import os
    if os.path.isdir(_STATIC_DIR):
        application.mount("/assets", StaticFiles(directory=f"{_STATIC_DIR}/assets"), name="assets")

        @application.get("/{full_path:path}", include_in_schema=False)
        def spa_fallback(full_path: str) -> FileResponse:  # pylint: disable=unused-argument
            """Serve the SPA for all unmatched routes."""
            return FileResponse(f"{_STATIC_DIR}/index.html")

    return application


app = create_app()
