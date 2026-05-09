from __future__ import annotations

from discogs_player.use_cases.provider_readiness import build_provider_readiness_contract
from tests.provider_readiness_fixtures import make_capabilities, make_provider


def test_readiness_example_missing_discogs_token():
    caps = make_capabilities(
        spotify_addon_available=False,
        spotify_configured=False,
        spotify_action_label="Enable Spotify (optional)",
        spotify_status_message="Spotify addon unavailable.",
        providers=(),
    )
    contract = build_provider_readiness_contract(
        app_capabilities=caps,
        discogs_configured=False,
        collection_synced=False,
    )
    assert contract["summary"]["onboarding_state"] == "needs_required_setup"
    assert contract["core_service"]["required"] is True
    assert contract["core_service"]["configured"] is False
    assert contract["summary"]["required_services_configured"] is False


def test_readiness_example_discogs_configured_optional_not_ready():
    caps = make_capabilities(
        spotify_addon_available=False,
        spotify_configured=False,
        spotify_action_label="Enable Spotify (optional)",
        spotify_status_message="Spotify addon unavailable.",
        providers=(
            make_provider(
                provider_id="spotify",
                display_name="Spotify",
                importable=False,
                addon_available=False,
                configured=False,
                action_label="Unavailable",
                status_message="Spotify addon unavailable.",
            ),
        ),
    )
    contract = build_provider_readiness_contract(
        app_capabilities=caps,
        discogs_configured=True,
        collection_synced=True,
    )
    assert contract["summary"]["onboarding_state"] == "core_ready_optional_pending"
    assert contract["summary"]["degraded_mode"] is True
    assert contract["summary"]["ready_provider_count"] == 0


def test_readiness_example_spotify_ready():
    caps = make_capabilities(
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
    )
    contract = build_provider_readiness_contract(
        app_capabilities=caps,
        discogs_configured=True,
        collection_synced=True,
    )
    assert contract["summary"]["onboarding_state"] == "ready"
    assert contract["summary"]["ready_provider_count"] == 1
    assert contract["providers"][0]["readiness"] == "ready"


def test_readiness_example_optional_provider_disabled():
    caps = make_capabilities(
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
    )
    contract = build_provider_readiness_contract(
        app_capabilities=caps,
        discogs_configured=True,
        collection_synced=True,
    )
    provider = contract["providers"][0]
    assert provider["provider_id"] == "youtube_music"
    assert provider["readiness"] == "unavailable"
    assert "disabled" in provider["degraded_reasons"]
