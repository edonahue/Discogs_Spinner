"""Spotify implementation of the generic player backend interface."""

from __future__ import annotations

import importlib.util
from typing import Callable, cast

from discogs_player.integrations.player_backend import (
    PlayerApiError,
    PlayerAuthError,
    PlayerBackend,
    PlayerDependencyError,
    PlayerPlaybackError,
    ProviderDescriptor,
)
from discogs_player.integrations.spotify.oauth import (
    SpotifyAuthError,
    SpotifyDependencyError,
    get_spotify_auth_diagnostics,
    get_spotify_access_token,
    has_spotify_configuration,
    run_spotify_oauth_login,
)
from discogs_player.integrations.spotify.spotify_client import (
    SpotifyApiError,
    SpotifyClient,
    SpotifyPlaybackError,
)


def _to_int(value: object | None, *, default: int) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped and stripped.lstrip("-").isdigit():
            return int(stripped)
    return default


def _to_bool(value: object | None, *, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return default


def _to_optional_str(value: object | None) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _to_scopes(value: object | None) -> list[str] | tuple[str, ...] | None:
    if value is None:
        return None
    if isinstance(value, tuple):
        return tuple(str(item).strip() for item in value if str(item).strip())
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return None


def _to_authorization_callback(
    value: object | None,
) -> Callable[[str], None] | None:
    if callable(value):
        return cast(Callable[[str], None], value)
    return None


def _to_manual_input_callback(value: object | None) -> Callable[[], str] | None:
    if callable(value):
        return cast(Callable[[], str], value)
    return None


class SpotifyPlayerBackend(PlayerBackend):
    @property
    def name(self) -> str:
        return "spotify"

    @classmethod
    def addon_available(cls) -> bool:
        return importlib.util.find_spec("keyring") is not None

    @classmethod
    def provider_descriptor(cls) -> ProviderDescriptor:
        return {
            "auth_required": True,
            "supported_capabilities": [
                "playback",
                "device_selection",
                "catalog_matching",
                "oauth_login",
                "auth_diagnostics",
            ],
            "setup_url": "https://developer.spotify.com/dashboard",
            "oauth_guide_url": (
                "https://developer.spotify.com/documentation/web-api/tutorials/code-flow"
            ),
            "next_actions_when_unconfigured": [
                "Run `dplayer auth spotify-doctor`.",
                "Run `dplayer auth spotify --open-browser`.",
            ],
            "can_skip_setup": True,
            "can_retry_setup": True,
        }

    def _ensure_addon(self) -> None:
        if not self.addon_available():
            raise PlayerDependencyError(
                "Enable Spotify (optional) with `pip install \".[spotify]\"`."
            )

    def is_configured(self, *, conn=None) -> bool:
        if not self.addon_available():
            return False
        return has_spotify_configuration(conn=conn)

    def _client(self, *, conn=None) -> SpotifyClient:
        self._ensure_addon()
        try:
            token = get_spotify_access_token(conn=conn)
            return SpotifyClient(access_token=token)
        except SpotifyDependencyError as exc:
            raise PlayerDependencyError(str(exc)) from exc
        except SpotifyAuthError as exc:
            raise PlayerAuthError(str(exc)) from exc

    def list_devices(self, *, conn=None) -> list[dict[str, object]]:
        client = self._client(conn=conn)
        try:
            return client.list_devices()
        except SpotifyAuthError as exc:
            raise PlayerAuthError(str(exc)) from exc
        except SpotifyApiError as exc:
            raise PlayerApiError(str(exc)) from exc

    def start_album_playback(
        self,
        provider_album_id: str,
        *,
        device_id: str | None = None,
        conn=None,
    ) -> None:
        client = self._client(conn=conn)
        try:
            client.start_album_playback(provider_album_id, device_id=device_id)
        except SpotifyAuthError as exc:
            raise PlayerAuthError(str(exc)) from exc
        except SpotifyPlaybackError as exc:
            raise PlayerPlaybackError(str(exc)) from exc
        except SpotifyApiError as exc:
            raise PlayerApiError(str(exc)) from exc

    def create_matching_client(self, *, conn=None) -> SpotifyClient:
        return self._client(conn=conn)

    def run_oauth_login(self, **kwargs: object) -> dict[str, object]:
        self._ensure_addon()
        try:
            listen_host = _to_optional_str(kwargs.get("listen_host")) or "127.0.0.1"
            listen_port = _to_int(kwargs.get("listen_port"), default=8765)
            timeout_seconds = _to_int(kwargs.get("timeout_seconds"), default=180)
            scopes = _to_scopes(kwargs.get("scopes"))
            open_browser = _to_bool(kwargs.get("open_browser"), default=False)
            manual_mode = _to_bool(kwargs.get("manual_mode"), default=False)
            manual_callback_url = _to_optional_str(kwargs.get("manual_callback_url"))
            manual_code = _to_optional_str(kwargs.get("manual_code"))
            allow_manual_fallback = _to_bool(
                kwargs.get("allow_manual_fallback"),
                default=False,
            )
            on_authorization_url = _to_authorization_callback(
                kwargs.get("on_authorization_url")
            )
            on_manual_authorization_input = _to_manual_input_callback(
                kwargs.get("on_manual_authorization_input")
            )

            return run_spotify_oauth_login(
                listen_host=listen_host,
                listen_port=listen_port,
                timeout_seconds=timeout_seconds,
                scopes=scopes,
                open_browser=open_browser,
                manual_mode=manual_mode,
                manual_callback_url=manual_callback_url,
                manual_code=manual_code,
                allow_manual_fallback=allow_manual_fallback,
                on_authorization_url=on_authorization_url,
                on_manual_authorization_input=on_manual_authorization_input,
                conn=kwargs.get("conn"),
            )
        except SpotifyDependencyError as exc:
            raise PlayerDependencyError(str(exc)) from exc
        except SpotifyAuthError as exc:
            raise PlayerAuthError(str(exc)) from exc

    def auth_diagnostics(self, *, conn=None, **kwargs: object) -> dict[str, object]:
        self._ensure_addon()
        try:
            listen_host = _to_optional_str(kwargs.get("listen_host")) or "127.0.0.1"
            listen_port = _to_int(kwargs.get("listen_port"), default=8765)
            diagnostics = get_spotify_auth_diagnostics(
                conn=kwargs.get("conn", conn),
                listen_host=listen_host,
                listen_port=listen_port,
            )
            diagnostics["backend"] = self.name
            diagnostics["addon_available"] = True
            return diagnostics
        except SpotifyDependencyError as exc:
            raise PlayerDependencyError(str(exc)) from exc
        except SpotifyAuthError as exc:
            raise PlayerAuthError(str(exc)) from exc
