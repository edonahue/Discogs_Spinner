"""Exception mapping for API routes."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from discogs_player.integrations.player_backend import (
    PlayerApiError,
    PlayerAuthError,
    PlayerDependencyError,
    PlayerPlaybackError,
)
from discogs_player.services.discogs_client import (
    DiscogsApiError,
    DiscogsAuthError,
    DiscogsDependencyError,
)
from discogs_player.services.matching import MatchingDependencyError
from discogs_player.services.sync_manager import MissingDiscogsTokenError
from discogs_player.use_cases.play_release import (
    MissingLastSpinError,
    MissingSpotifyMappingError,
    NoPlayableDeviceError,
)


def _is_retryable_text(message: str) -> bool:
    text = message.lower()
    return "429" in text or "rate limit" in text or "timeout" in text


def map_exception(exc: Exception) -> tuple[int, dict[str, Any]]:
    message = str(exc).strip() or exc.__class__.__name__

    if isinstance(exc, MissingDiscogsTokenError):
        return (
            400,
            {
                "code": "missing_discogs_token",
                "message": message,
                "retryable": False,
                "details": None,
            },
        )
    if isinstance(exc, ValueError):
        return (
            400,
            {
                "code": "invalid_request",
                "message": message,
                "retryable": False,
                "details": None,
            },
        )
    if isinstance(exc, (DiscogsAuthError, PlayerAuthError)):
        return (
            401,
            {
                "code": "auth_error",
                "message": message,
                "retryable": False,
                "details": None,
            },
        )
    if isinstance(
        exc,
        (
            DiscogsDependencyError,
            MatchingDependencyError,
            PlayerDependencyError,
        ),
    ):
        return (
            503,
            {
                "code": "dependency_unavailable",
                "message": message,
                "retryable": False,
                "details": None,
            },
        )
    if isinstance(exc, (MissingLastSpinError, MissingSpotifyMappingError, NoPlayableDeviceError)):
        return (
            409,
            {
                "code": "operation_blocked",
                "message": message,
                "retryable": False,
                "details": None,
            },
        )
    if isinstance(exc, (DiscogsApiError, PlayerApiError, PlayerPlaybackError)):
        return (
            502,
            {
                "code": "upstream_api_error",
                "message": message,
                "retryable": _is_retryable_text(message),
                "details": None,
            },
        )

    return (
        500,
        {
            "code": "internal_server_error",
            "message": message,
            "retryable": False,
            "details": None,
        },
    )


def raise_http_exception_for(exc: Exception) -> None:
    status_code, payload = map_exception(exc)
    raise HTTPException(status_code=status_code, detail=payload) from exc
