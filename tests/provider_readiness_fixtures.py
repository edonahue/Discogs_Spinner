from __future__ import annotations

from discogs_player.capabilities import (
    AppCapabilities,
    ProviderCapability,
    SpotifyCapabilities,
)


def make_provider(
    *,
    provider_id: str,
    display_name: str,
    listed: bool = True,
    enabled: bool = True,
    importable: bool = True,
    addon_available: bool = True,
    configured: bool = True,
    action_label: str = "Ready",
    status_message: str = "Provider is ready.",
    docs_url: str | None = None,
    experimental: bool = False,
    experimental_flag: str | None = None,
) -> ProviderCapability:
    return ProviderCapability(
        provider_id=provider_id,
        display_name=display_name,
        listed=listed,
        enabled=enabled,
        importable=importable,
        addon_available=addon_available,
        configured=configured,
        action_label=action_label,
        status_message=status_message,
        docs_url=docs_url,
        experimental=experimental,
        experimental_flag=experimental_flag,
    )


def make_capabilities(
    *,
    spotify_addon_available: bool,
    spotify_configured: bool,
    spotify_action_label: str = "Spotify Ready",
    spotify_status_message: str = "Spotify playback and matching are available.",
    providers: tuple[ProviderCapability, ...] = (),
) -> AppCapabilities:
    return AppCapabilities(
        spotify=SpotifyCapabilities(
            addon_available=spotify_addon_available,
            configured=spotify_configured,
            action_label=spotify_action_label,
            status_message=spotify_status_message,
        ),
        providers=providers,
    )

