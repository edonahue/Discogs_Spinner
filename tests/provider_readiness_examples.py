from __future__ import annotations

from types import SimpleNamespace

from discogs_player.use_cases.provider_readiness import build_provider_readiness_contract
from tests.provider_readiness_fixtures import make_capabilities, make_provider


def build_provider_readiness_examples() -> dict[str, dict[str, object]]:
    examples: dict[str, dict[str, object]] = {}

    examples["missing_discogs_token"] = build_provider_readiness_contract(
        app_capabilities=make_capabilities(
            spotify_addon_available=False,
            spotify_configured=False,
            spotify_action_label="Enable Spotify (optional)",
            spotify_status_message="Spotify addon unavailable.",
            providers=(),
        ),
        discogs_configured=False,
        collection_synced=False,
    )

    examples["discogs_configured_needs_initial_sync"] = build_provider_readiness_contract(
        app_capabilities=make_capabilities(
            spotify_addon_available=False,
            spotify_configured=False,
            providers=(),
        ),
        discogs_configured=True,
        collection_synced=False,
    )

    examples["discogs_ready_optional_skipped"] = build_provider_readiness_contract(
        app_capabilities=SimpleNamespace(providers=()),
        discogs_configured=True,
        collection_synced=True,
    )

    examples["spotify_ready"] = build_provider_readiness_contract(
        app_capabilities=make_capabilities(
            spotify_addon_available=True,
            spotify_configured=True,
            providers=(
                make_provider(
                    provider_id="spotify",
                    display_name="Spotify",
                    importable=True,
                    addon_available=True,
                    configured=True,
                    action_label="Ready",
                    status_message="Spotify provider is ready.",
                ),
            ),
        ),
        discogs_configured=True,
        collection_synced=True,
    )

    examples["experimental_youtube_music_disabled"] = build_provider_readiness_contract(
        app_capabilities=make_capabilities(
            spotify_addon_available=False,
            spotify_configured=False,
            providers=(
                make_provider(
                    provider_id="youtube_music",
                    display_name="YouTube Music",
                    enabled=False,
                    importable=False,
                    addon_available=False,
                    configured=False,
                    action_label="Planned",
                    status_message="Provider listed but disabled.",
                    experimental=True,
                    experimental_flag="DP_ENABLE_EXPERIMENTAL_YOUTUBE_MUSIC",
                ),
            ),
        ),
        discogs_configured=True,
        collection_synced=True,
    )

    examples["provider_unavailable"] = build_provider_readiness_contract(
        app_capabilities=make_capabilities(
            spotify_addon_available=False,
            spotify_configured=False,
            providers=(
                make_provider(
                    provider_id="alt_provider",
                    display_name="Alt Provider",
                    importable=False,
                    addon_available=False,
                    configured=False,
                    action_label="Unavailable",
                    status_message="Provider backend is not installed.",
                ),
            ),
        ),
        discogs_configured=True,
        collection_synced=True,
    )

    examples["provider_unauthenticated"] = build_provider_readiness_contract(
        app_capabilities=make_capabilities(
            spotify_addon_available=True,
            spotify_configured=False,
            providers=(
                make_provider(
                    provider_id="spotify",
                    display_name="Spotify",
                    importable=True,
                    addon_available=True,
                    configured=False,
                    action_label="Connect Spotify",
                    status_message="Spotify addon is installed but not configured.",
                ),
            ),
        ),
        discogs_configured=True,
        collection_synced=True,
    )

    examples["degraded_mode_optional_pending"] = build_provider_readiness_contract(
        app_capabilities=make_capabilities(
            spotify_addon_available=False,
            spotify_configured=False,
            providers=(
                make_provider(
                    provider_id="spotify",
                    display_name="Spotify",
                    importable=True,
                    addon_available=True,
                    configured=False,
                    action_label="Connect Spotify",
                    status_message="Spotify addon is installed but not configured.",
                ),
                make_provider(
                    provider_id="youtube_music",
                    display_name="YouTube Music",
                    enabled=False,
                    importable=False,
                    addon_available=False,
                    configured=False,
                    action_label="Planned",
                    status_message="Provider listed but disabled.",
                    experimental=True,
                    experimental_flag="DP_ENABLE_EXPERIMENTAL_YOUTUBE_MUSIC",
                ),
            ),
        ),
        discogs_configured=True,
        collection_synced=True,
    )

    return examples
