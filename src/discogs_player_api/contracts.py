"""Shared API envelope helpers."""

from __future__ import annotations

from typing import Any


def success_envelope(
    data: object,
    *,
    meta: dict[str, object] | None = None,
) -> dict[str, Any]:
    return {
        "ok": True,
        "data": data,
        "error": None,
        "meta": dict(meta or {}),
    }


def error_envelope(
    *,
    code: str,
    message: str,
    retryable: bool = False,
    details: object | None = None,
    meta: dict[str, object] | None = None,
) -> dict[str, Any]:
    return {
        "ok": False,
        "data": None,
        "error": {
            "code": str(code).strip() or "unknown_error",
            "message": str(message).strip() or "Unexpected API error.",
            "retryable": bool(retryable),
            "details": details,
        },
        "meta": dict(meta or {}),
    }
