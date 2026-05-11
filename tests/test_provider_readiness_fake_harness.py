from __future__ import annotations

import pytest

from discogs_player.capabilities import AppCapabilities, ProviderCapability, SpotifyCapabilities
from discogs_player.use_cases import provider_readiness


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


def _caps(*providers: ProviderCapability) -> AppCapabilities:
    return AppCapabilities(
        spotify=SpotifyCapabilities(
            addon_available=False,
            configured=False,
            action_label="Enable Spotify (optional)",
            status_message="Spotify addon unavailable.",
        ),
        providers=providers,
    )


@pytest.mark.parametrize(
    ("name", "provider", "descriptor", "expected"),
    [
        pytest.param(
            "ready",
            _provider(provider_id="fake_ready", display_name="Fake Ready"),
            {
                "auth_required": True,
                "supported_capabilities": ["playback", "catalog_matching"],
            },
            {"readiness": "ready", "auth_state": "authenticated"},
            id="provider-ready",
        ),
        pytest.param(
            "unavailable",
            _provider(
                provider_id="fake_unavailable",
                display_name="Fake Unavailable",
                importable=False,
                addon_available=False,
                configured=False,
                action_label="Unavailable",
                status_message="Provider backend not installed.",
            ),
            {"auth_required": True},
            {
                "readiness": "unavailable",
                "degraded_reasons": {"backend_not_installed"},
            },
            id="provider-unavailable",
        ),
        pytest.param(
            "disabled",
            _provider(
                provider_id="fake_disabled",
                display_name="Fake Disabled",
                enabled=False,
                importable=False,
                addon_available=False,
                configured=False,
                action_label="Disabled",
                status_message="Provider disabled by policy.",
            ),
            {"auth_required": True},
            {
                "readiness": "unavailable",
                "degraded_reasons": {"disabled", "backend_not_installed"},
            },
            id="provider-disabled",
        ),
        pytest.param(
            "installed_not_configured",
            _provider(
                provider_id="fake_not_configured",
                display_name="Fake Not Configured",
                importable=True,
                addon_available=True,
                configured=False,
                action_label="Connect",
                status_message="Addon installed but setup pending.",
            ),
            {"auth_required": False},
            {
                "readiness": "degraded",
                "auth_state": "not_required",
                "degraded_reasons": {"not_configured"},
            },
            id="installed-but-not-configured",
        ),
        pytest.param(
            "configured_unauthenticated",
            _provider(
                provider_id="fake_unauth",
                display_name="Fake Unauthenticated",
                importable=True,
                addon_available=True,
                configured=False,
                action_label="Re-authenticate",
                status_message="Stored config exists but auth is missing.",
            ),
            {"auth_required": True},
            {
                "readiness": "degraded",
                "auth_state": "unauthenticated",
                "degraded_reasons": {"unauthenticated"},
            },
            id="configured-but-unauthenticated",
        ),
        pytest.param(
            "limited_capability",
            _provider(
                provider_id="fake_limited",
                display_name="Fake Limited",
                configured=True,
                status_message="Matching-only provider.",
            ),
            {"auth_required": False, "supported_capabilities": ["catalog_matching"]},
            {
                "readiness": "ready",
                "supported_capabilities": ["catalog_matching"],
            },
            id="limited-capability",
        ),
        pytest.param(
            "browser_playback",
            _provider(
                provider_id="fake_browser",
                display_name="Fake Browser",
                configured=True,
                status_message="Browser playback only.",
            ),
            {"auth_required": False, "supported_capabilities": ["browser_playback"]},
            {
                "readiness": "ready",
                "supported_capabilities": ["browser_playback"],
            },
            id="browser-only-playback",
        ),
        pytest.param(
            "no_auth_required",
            _provider(
                provider_id="fake_no_auth",
                display_name="Fake No Auth",
                configured=True,
                status_message="No account required.",
            ),
            {
                "auth_required": False,
                "supported_capabilities": ["playback"],
                "next_actions_when_unconfigured": [
                    "Set local endpoint for LAN playback.",
                ],
            },
            {
                "readiness": "ready",
                "auth_state": "not_required",
            },
            id="no-auth-required",
        ),
        pytest.param(
            "experimental_flagged",
            _provider(
                provider_id="fake_experimental",
                display_name="Fake Experimental",
                enabled=False,
                importable=False,
                addon_available=False,
                configured=False,
                action_label="Planned",
                status_message="Provider is experimental.",
                experimental=True,
                experimental_flag="DP_ENABLE_FAKE_EXPERIMENTAL",
            ),
            {"auth_required": False, "supported_capabilities": ["browser_playback"]},
            {
                "readiness": "unavailable",
                "degraded_reasons": {"disabled", "backend_not_installed"},
                "next_action_contains": "DP_ENABLE_FAKE_EXPERIMENTAL=1",
            },
            id="experimental-behind-flag",
        ),
    ],
)
def test_fake_provider_harness_covers_future_provider_readiness_states(
    monkeypatch,
    name: str,
    provider: ProviderCapability,
    descriptor: dict[str, object],
    expected: dict[str, object],
):
    descriptor_map = {provider.provider_id: descriptor}
    monkeypatch.setattr(
        provider_readiness,
        "provider_descriptor",
        lambda provider_id: descriptor_map.get(provider_id, {}),
    )
    contract = provider_readiness.build_provider_readiness_contract(
        app_capabilities=_caps(provider),
        discogs_configured=True,
        collection_synced=True,
    )

    row = contract["providers"][0]
    assert row["provider_id"] == provider.provider_id, name
    assert row["readiness"] == expected["readiness"], name

    expected_auth_state = expected.get("auth_state")
    if isinstance(expected_auth_state, str):
        assert row["auth_state"] == expected_auth_state, name

    expected_reasons = expected.get("degraded_reasons")
    if isinstance(expected_reasons, set):
        assert set(row["degraded_reasons"]) == expected_reasons, name

    expected_capabilities = expected.get("supported_capabilities")
    if isinstance(expected_capabilities, list):
        assert row["supported_capabilities"] == expected_capabilities, name

    expected_action_fragment = expected.get("next_action_contains")
    if isinstance(expected_action_fragment, str):
        assert any(
            expected_action_fragment in str(item)
            for item in row.get("next_actions", [])
        ), name

