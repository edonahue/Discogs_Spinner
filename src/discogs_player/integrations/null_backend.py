"""Null backend used when Spotify addon is not installed."""

from __future__ import annotations

from typing import Any, NoReturn

from discogs_player.integrations.player_backend import (
    PlayerBackend,
    PlayerDependencyError,
)


_NULL_BACKEND_MESSAGE = (
    "Enable Spotify (optional) with `pip install \".[spotify]\"` to use playback, "
    "matching, device, and auth commands."
)


class NullPlayerBackend(PlayerBackend):
    @property
    def name(self) -> str:
        return "null"

    @classmethod
    def addon_available(cls) -> bool:
        return False

    def is_configured(self, *, conn=None) -> bool:
        _ = conn
        return False

    def _raise_unavailable(self) -> NoReturn:
        raise PlayerDependencyError(_NULL_BACKEND_MESSAGE)

    def list_devices(self, *, conn=None) -> list[dict[str, object]]:
        _ = conn
        self._raise_unavailable()

    def start_album_playback(
        self,
        provider_album_id: str,
        *,
        device_id: str | None = None,
        conn=None,
    ) -> None:
        _ = (provider_album_id, device_id, conn)
        self._raise_unavailable()

    def create_matching_client(self, *, conn=None) -> Any:
        _ = conn
        self._raise_unavailable()

    def run_oauth_login(self, **kwargs: object) -> dict[str, object]:
        _ = kwargs
        self._raise_unavailable()

    def auth_diagnostics(self, *, conn=None, **kwargs: object) -> dict[str, object]:
        _ = (conn, kwargs)
        return {
            "backend": "null",
            "diagnosis": "addon_missing",
            "addon_available": False,
            "configured": False,
            "recommended_action": 'Install plus profile: pip install -e ".[spotify]"',
            "status_message": _NULL_BACKEND_MESSAGE,
        }
