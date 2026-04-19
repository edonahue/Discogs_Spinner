"""FastAPI application factory for discogs_player."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from discogs_player import __version__ as APP_VERSION
from discogs_player_api.contracts import error_envelope, success_envelope
from discogs_player_api.routers.cache import router as cache_router
from discogs_player_api.routers.catalog import router as catalog_router
from discogs_player_api.routers.matching import router as matching_router
from discogs_player_api.routers.playback import router as playback_router
from discogs_player_api.routers.setup import router as setup_router
from discogs_player_api.routers.share import router as share_router
from discogs_player_api.routers.status import router as status_router
from discogs_player_api.routers.sync import router as sync_router
from discogs_player_api.routers.value import router as value_router


def _error_from_detail(detail: object) -> dict[str, Any]:
    if isinstance(detail, dict):
        code = str(detail.get("code") or "").strip() or "http_error"
        message = str(detail.get("message") or "").strip() or "HTTP error"
        retryable = bool(detail.get("retryable"))
        return {
            "code": code,
            "message": message,
            "retryable": retryable,
            "details": detail.get("details"),
        }
    return {
        "code": "http_error",
        "message": str(detail),
        "retryable": False,
        "details": None,
    }


def create_app() -> FastAPI:
    app = FastAPI(
        title="discogs_player API",
        version=APP_VERSION,
        summary="Local-first Discogs Player API for web and desktop clients.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "tauri://localhost"],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Accept"],
    )

    @app.get("/healthz")
    def healthz() -> dict[str, object]:
        return success_envelope({"status": "ok"})

    @app.exception_handler(HTTPException)
    async def http_exception_handler(  # type: ignore[override]
        _request: Request,
        exc: HTTPException,
    ) -> JSONResponse:
        error = _error_from_detail(exc.detail)
        payload = error_envelope(
            code=error["code"],
            message=error["message"],
            retryable=bool(error["retryable"]),
            details=error.get("details"),
        )
        return JSONResponse(status_code=int(exc.status_code), content=payload)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(  # type: ignore[override]
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        payload = error_envelope(
            code="request_validation_failed",
            message="Request validation failed.",
            retryable=False,
            details={"errors": exc.errors()},
        )
        return JSONResponse(status_code=422, content=payload)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(  # type: ignore[override]
        _request: Request,
        exc: Exception,
    ) -> JSONResponse:
        payload = error_envelope(
            code="internal_server_error",
            message=str(exc) or "Internal server error.",
            retryable=False,
            details=None,
        )
        return JSONResponse(status_code=500, content=payload)

    api_prefix = "/api/v1"
    app.include_router(setup_router, prefix=api_prefix)
    app.include_router(status_router, prefix=api_prefix)
    app.include_router(catalog_router, prefix=api_prefix)
    app.include_router(sync_router, prefix=api_prefix)
    app.include_router(matching_router, prefix=api_prefix)
    app.include_router(playback_router, prefix=api_prefix)
    app.include_router(value_router, prefix=api_prefix)
    app.include_router(cache_router, prefix=api_prefix)
    app.include_router(share_router, prefix=api_prefix)

    return app
