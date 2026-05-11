from __future__ import annotations

from discogs_player.capabilities import AppCapabilities, ProviderCapability, SpotifyCapabilities
from discogs_player.use_cases.provider_readiness import build_provider_readiness_contract

_CONTRACT_KEYS = {
    "schema_version",
    "core_service",
    "providers",
    "next_actions",
    "summary",
}

_CORE_SERVICE_KEYS = {
    "service_id",
    "display_name",
    "required",
    "optional",
    "configured",
    "auth_required",
    "auth_state",
    "readiness",
    "degraded_reasons",
    "supported_capabilities",
    "next_actions",
    "can_skip_setup",
    "can_retry_setup",
    "setup_url",
    "status_message",
    "action_label",
}

_PROVIDER_KEYS = {
    "provider_id",
    "display_name",
    "required",
    "optional",
    "listed",
    "enabled",
    "installed",
    "addon_available",
    "configured",
    "auth_required",
    "auth_state",
    "readiness",
    "degraded_reasons",
    "supported_capabilities",
    "next_actions",
    "can_skip_setup",
    "can_retry_setup",
    "setup_url",
    "docs_url",
    "oauth_guide_url",
    "experimental",
    "experimental_flag",
    "status_message",
    "action_label",
}

_SUMMARY_KEYS = {
    "required_services_configured",
    "optional_provider_count",
    "ready_provider_count",
    "degraded_mode",
    "onboarding_state",
    "collection_synced",
    "next_actions",
    "can_skip_optional_setup",
}


def _provider(
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


def test_provider_readiness_contract_exposes_required_core_and_optional_providers():
    caps = AppCapabilities(
        spotify=SpotifyCapabilities(
            addon_available=True,
            configured=False,
            action_label="Connect Spotify",
            status_message="Spotify addon is installed but not configured.",
        ),
        providers=(
            _provider(
                provider_id="spotify",
                display_name="Spotify",
                addon_available=True,
                configured=False,
                action_label="Connect Spotify",
                status_message="Spotify addon is installed but not configured.",
            ),
        ),
    )

    contract = build_provider_readiness_contract(
        app_capabilities=caps,
        discogs_configured=True,
        collection_synced=True,
    )

    assert contract["schema_version"] == 2
    assert isinstance(contract.get("next_actions"), list)
    core = contract["core_service"]
    assert core["service_id"] == "discogs"
    assert core["required"] is True
    assert core["configured"] is True

    providers = contract["providers"]
    assert isinstance(providers, list)
    assert providers[0]["provider_id"] == "spotify"
    assert providers[0]["optional"] is True
    assert providers[0]["auth_required"] is True
    assert providers[0]["auth_state"] == "unauthenticated"
    assert providers[0]["readiness"] == "degraded"
    assert "unauthenticated" in providers[0]["degraded_reasons"]
    assert providers[0]["can_skip_setup"] is True
    assert providers[0]["can_retry_setup"] is True
    assert "catalog_matching" in providers[0]["supported_capabilities"]
    assert "setup_url" in providers[0]
    assert "oauth_guide_url" in providers[0]


def test_provider_readiness_contract_marks_disabled_provider_as_unavailable():
    caps = AppCapabilities(
        spotify=SpotifyCapabilities(
            addon_available=False,
            configured=False,
            action_label="Enable Spotify (optional)",
            status_message="Spotify addon unavailable.",
        ),
        providers=(
            _provider(
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
        discogs_configured=False,
        collection_synced=False,
    )

    core = contract["core_service"]
    assert core["configured"] is False
    assert core["readiness"] == "blocked"

    provider = contract["providers"][0]
    assert provider["provider_id"] == "youtube_music"
    assert provider["readiness"] == "unavailable"
    assert "disabled" in provider["degraded_reasons"]
    assert "backend_not_installed" in provider["degraded_reasons"]

    summary = contract["summary"]
    assert summary["required_services_configured"] is False
    assert summary["collection_synced"] is False
    assert summary["onboarding_state"] == "needs_required_setup"
    assert summary["can_skip_optional_setup"] is True


def test_provider_readiness_contract_summary_counts_ready_providers():
    caps = AppCapabilities(
        spotify=SpotifyCapabilities(
            addon_available=True,
            configured=True,
            action_label="Spotify Ready",
            status_message="Spotify playback and matching are available.",
        ),
        providers=(
            _provider(
                provider_id="spotify",
                display_name="Spotify",
                configured=True,
            ),
            _provider(
                provider_id="youtube_music",
                display_name="YouTube Music",
                configured=True,
                status_message="YouTube Music provider is ready.",
            ),
        ),
    )

    contract = build_provider_readiness_contract(
        app_capabilities=caps,
        discogs_configured=True,
        collection_synced=True,
    )

    summary = contract["summary"]
    assert summary["required_services_configured"] is True
    assert summary["optional_provider_count"] == 2
    assert summary["ready_provider_count"] == 2
    assert summary["degraded_mode"] is False
    assert summary["onboarding_state"] == "ready"


def test_provider_readiness_contract_stability_keys():
    caps = AppCapabilities(
        spotify=SpotifyCapabilities(
            addon_available=False,
            configured=False,
            action_label="Enable Spotify (optional)",
            status_message="Spotify addon unavailable.",
        ),
        providers=(),
    )
    contract = build_provider_readiness_contract(
        app_capabilities=caps,
        discogs_configured=False,
        collection_synced=False,
    )
    assert set(contract.keys()) == _CONTRACT_KEYS
    assert set(contract["summary"].keys()) == _SUMMARY_KEYS
    assert set(contract["core_service"].keys()) == _CORE_SERVICE_KEYS


def test_provider_readiness_contract_provider_field_stability():
    caps = AppCapabilities(
        spotify=SpotifyCapabilities(
            addon_available=True,
            configured=False,
            action_label="Connect Spotify",
            status_message="Spotify addon is installed but not configured.",
        ),
        providers=(
            _provider(
                provider_id="spotify",
                display_name="Spotify",
                addon_available=True,
                configured=False,
                action_label="Connect Spotify",
                status_message="Spotify addon is installed but not configured.",
            ),
        ),
    )
    contract = build_provider_readiness_contract(
        app_capabilities=caps,
        discogs_configured=True,
        collection_synced=True,
    )
    providers = contract["providers"]
    assert isinstance(providers, list)
    assert providers
    assert set(providers[0].keys()) == _PROVIDER_KEYS
