"""Runtime capability detection for optional integrations."""

from __future__ import annotations

from dataclasses import dataclass, field

from discogs_player.integrations.player_backend import PlayerBackend
from discogs_player.integrations.provider_registry import (
    experimental_flag,
    get_backend,
    get_backend_type,
    listed_provider_ids,
    provider_metadata,
)

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
class ProviderCapability:
    provider_id: str
    display_name: str
    listed: bool
    enabled: bool
    importable: bool
    addon_available: bool
    configured: bool
    action_label: str
    status_message: str
    docs_url: str | None = None
    experimental: bool = False
    experimental_flag: str | None = None


@dataclass(frozen=True)
class AppCapabilities:
    spotify: SpotifyCapabilities
    providers: tuple[ProviderCapability, ...] = field(default_factory=tuple)


def _spotify_backend_type() -> type[PlayerBackend] | None:
    return get_backend_type("spotify")


def get_player_backend() -> PlayerBackend:
    return get_backend("spotify")


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

    providers: list[ProviderCapability] = []
    for provider_id in listed_provider_ids():
        metadata = provider_metadata(provider_id) or {}
        display_name = str(metadata.get("display_name") or provider_id)
        docs_url = metadata.get("docs_url")
        flag = experimental_flag(provider_id)
        enabled = bool(metadata.get("enabled", True))

        backend_cls = get_backend_type(provider_id) if enabled else None
        importable = backend_cls is not None
        provider_addon_available = False
        provider_configured = False

        if backend_cls is not None:
            try:
                provider_backend = backend_cls()
                provider_addon_available = provider_backend.addon_available()
                if provider_addon_available:
                    try:
                        provider_configured = provider_backend.is_configured(conn=conn)
                    except Exception:
                        provider_configured = False
            except Exception:
                provider_addon_available = False
                provider_configured = False

        if not enabled and flag:
            provider_action_label = "Planned"
            provider_status_message = (
                f"{display_name} provider is listed but disabled. "
                f"Set {flag}=1 to expose experimental scaffolding."
            )
        elif not importable:
            provider_action_label = "Unavailable"
            provider_status_message = (
                f"{display_name} provider scaffold is listed but not installed."
            )
        elif not provider_addon_available:
            provider_action_label = "Unavailable"
            provider_status_message = (
                f"{display_name} provider backend is present but addon dependencies are unavailable."
            )
        elif not provider_configured:
            provider_action_label = "Connect"
            provider_status_message = (
                f"{display_name} provider addon is installed but not configured."
            )
        else:
            provider_action_label = "Ready"
            provider_status_message = f"{display_name} provider is ready."

        providers.append(
            ProviderCapability(
                provider_id=provider_id,
                display_name=display_name,
                listed=True,
                enabled=enabled,
                importable=importable,
                addon_available=provider_addon_available,
                configured=provider_configured,
                action_label=provider_action_label,
                status_message=provider_status_message,
                docs_url=docs_url if isinstance(docs_url, str) else None,
                experimental=bool(metadata.get("experimental", False)),
                experimental_flag=flag,
            )
        )

    return AppCapabilities(
        spotify=SpotifyCapabilities(
            addon_available=addon_available,
            configured=configured,
            action_label=action_label,
            status_message=status_message,
        ),
        providers=tuple(providers),
    )
