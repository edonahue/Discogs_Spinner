"""Runtime capability detection for optional integrations."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module

from discogs_player.integrations.null_backend import NullPlayerBackend
from discogs_player.integrations.player_backend import PlayerBackend

_SPOTIFY_DASHBOARD_URL = "https://developer.spotify.com/dashboard"
_SPOTIFY_OAUTH_GUIDE_URL = (
    "https://developer.spotify.com/documentation/web-api/tutorials/code-flow"
)


@dataclass(frozen=True)
class SpotifyCapabilities:
    addon_available: bool
    configured: bool
    action_label: str
    status_message: str


@dataclass(frozen=True)
class AppCapabilities:
    spotify: SpotifyCapabilities


def _spotify_backend_type() -> type[PlayerBackend] | None:
    try:
        module = import_module("discogs_player.integrations.spotify.backend")
    except ModuleNotFoundError as exc:
        missing = str(exc.name or "")
        if missing.startswith("discogs_player.integrations.spotify"):
            return None
        raise

    backend_cls = getattr(module, "SpotifyPlayerBackend", None)
    if not isinstance(backend_cls, type):
        return None
    if not issubclass(backend_cls, PlayerBackend):
        return None
    return backend_cls


def get_player_backend() -> PlayerBackend:
    backend_cls = _spotify_backend_type()
    if backend_cls is None:
        return NullPlayerBackend()

    backend = backend_cls()
    if not backend.addon_available():
        return NullPlayerBackend()
    return backend


def get_capabilities(conn=None) -> AppCapabilities:
    backend = get_player_backend()
    addon_available = backend.addon_available()

    configured = False
    if addon_available:
        try:
            configured = backend.is_configured(conn=conn)
        except Exception:
            configured = False

    if not addon_available:
        action_label = "Enable Spotify (optional)"
        status_message = (
            "Spotify addon is unavailable. Install with `pip install \".[spotify]\"` "
            f"or run `dplayer setup` for guided onboarding. Dashboard: {_SPOTIFY_DASHBOARD_URL}"
        )
    elif not configured:
        action_label = "Connect Spotify"
        status_message = (
            "Spotify addon is installed but not configured. Run `dplayer auth spotify` "
            "or `dplayer auth spotify-doctor`. "
            f"OAuth guide: {_SPOTIFY_OAUTH_GUIDE_URL}"
        )
    else:
        action_label = "Spotify Ready"
        status_message = "Spotify playback and matching are available."

    return AppCapabilities(
        spotify=SpotifyCapabilities(
            addon_available=addon_available,
            configured=configured,
            action_label=action_label,
            status_message=status_message,
        )
    )
