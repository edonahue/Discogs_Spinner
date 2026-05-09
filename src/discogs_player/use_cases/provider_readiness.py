"""Provider readiness contract for setup/status/onboarding surfaces."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

from discogs_player.capabilities import AppCapabilities, ProviderCapability, get_capabilities
from discogs_player.core.settings import get_discogs_token

_SPOTIFY_DASHBOARD_URL = "https://developer.spotify.com/dashboard"
_SPOTIFY_OAUTH_GUIDE_URL = (
    "https://developer.spotify.com/documentation/web-api/tutorials/code-flow"
)
_DISCOGS_TOKEN_URL = "https://www.discogs.com/settings/developers"

_PROVIDER_CAPABILITIES: dict[str, tuple[str, ...]] = {
    "spotify": (
        "playback",
        "device_selection",
        "catalog_matching",
        "oauth_login",
        "auth_diagnostics",
    ),
    "youtube_music": (
        "playback",
        "catalog_matching",
        "browser_playback",
    ),
}


def _provider_auth_required(provider_id: str) -> bool:
    return provider_id == "spotify"


def _provider_supported_capabilities(provider_id: str) -> list[str]:
    return list(_PROVIDER_CAPABILITIES.get(provider_id, ()))


def _provider_next_actions(provider: ProviderCapability) -> list[str]:
    if not provider.enabled and provider.experimental_flag:
        return [f"Set {provider.experimental_flag}=1 to enable provider scaffolding."]
    if not provider.importable:
        return ["Install provider dependencies before enabling this provider."]
    if not provider.addon_available:
        return ["Install optional addon dependencies for this provider."]
    if _provider_auth_required(provider.provider_id) and not provider.configured:
        return [
            "Run `dplayer auth spotify-doctor`.",
            "Run `dplayer auth spotify --open-browser`.",
            f"Spotify dashboard: {_SPOTIFY_DASHBOARD_URL}",
            f"Spotify OAuth guide: {_SPOTIFY_OAUTH_GUIDE_URL}",
        ]
    if not provider.configured:
        return ["Run provider auth/setup flow."]
    return ["Provider is ready for playback and matching."]


def _provider_degraded_reasons(provider: ProviderCapability) -> list[str]:
    reasons: list[str] = []
    if not provider.enabled:
        reasons.append("disabled")
    if not provider.importable:
        reasons.append("backend_not_installed")
    if provider.importable and not provider.addon_available:
        reasons.append("addon_unavailable")
    if provider.addon_available and _provider_auth_required(provider.provider_id) and not provider.configured:
        reasons.append("unauthenticated")
    if provider.addon_available and not _provider_auth_required(provider.provider_id) and not provider.configured:
        reasons.append("not_configured")
    return reasons


def _provider_readiness(provider: ProviderCapability) -> str:
    reasons = _provider_degraded_reasons(provider)
    if not reasons and provider.configured:
        return "ready"
    if not provider.importable or not provider.addon_available:
        return "unavailable"
    return "degraded"


def _provider_contract_row(provider: ProviderCapability) -> dict[str, object]:
    auth_required = _provider_auth_required(provider.provider_id)
    readiness = _provider_readiness(provider)
    degraded_reasons = _provider_degraded_reasons(provider)
    auth_state = "not_required"
    if auth_required:
        auth_state = "authenticated" if provider.configured else "unauthenticated"

    return {
        "provider_id": provider.provider_id,
        "display_name": provider.display_name,
        "required": False,
        "optional": True,
        "listed": provider.listed,
        "enabled": provider.enabled,
        "installed": provider.importable,
        "addon_available": provider.addon_available,
        "configured": provider.configured,
        "auth_required": auth_required,
        "auth_state": auth_state,
        "readiness": readiness,
        "degraded_reasons": degraded_reasons,
        "status_message": provider.status_message,
        "action_label": provider.action_label,
        "supported_capabilities": _provider_supported_capabilities(provider.provider_id),
        "can_skip_setup": True,
        "can_retry_setup": bool(not provider.configured or not provider.addon_available),
        "next_actions": _provider_next_actions(provider),
        "docs_url": provider.docs_url,
        "experimental": provider.experimental,
        "experimental_flag": provider.experimental_flag,
    }


def _discogs_contract_row(*, discogs_configured: bool) -> dict[str, object]:
    next_actions: list[str] = []
    if not discogs_configured:
        next_actions.extend(
            [
                f"Open token page: {_DISCOGS_TOKEN_URL}",
                'Set token via environment: export DISCOGS_TOKEN="your_discogs_personal_token"',
                "Or run: dplayer config set discogs_token <token>",
            ]
        )
    else:
        next_actions.append("Discogs core service is configured.")

    return {
        "service_id": "discogs",
        "display_name": "Discogs",
        "required": True,
        "optional": False,
        "configured": discogs_configured,
        "auth_required": True,
        "auth_state": "authenticated" if discogs_configured else "unauthenticated",
        "readiness": "ready" if discogs_configured else "blocked",
        "degraded_reasons": [] if discogs_configured else ["core_not_configured"],
        "status_message": (
            "Discogs token configured."
            if discogs_configured
            else "Discogs token missing."
        ),
        "action_label": "Configured" if discogs_configured else "Configure Discogs",
        "supported_capabilities": (
            ["collection_sync", "wantlist_sync", "market_value", "tracklist_cache"]
        ),
        "can_skip_setup": False,
        "can_retry_setup": True,
        "next_actions": next_actions,
        "setup_url": _DISCOGS_TOKEN_URL,
    }


def build_provider_readiness_contract(
    *,
    app_capabilities: AppCapabilities | object | None = None,
    discogs_configured: bool | None = None,
    collection_synced: bool | None = None,
) -> dict[str, object]:
    """Build provider/core readiness contract for all adapters."""

    capabilities = app_capabilities or get_capabilities()
    if discogs_configured is None:
        discogs_configured = bool(get_discogs_token())

    provider_rows: "OrderedDict[str, dict[str, object]]" = OrderedDict()
    raw_providers = getattr(capabilities, "providers", ())  # test stubs may omit this field
    for provider in raw_providers:
        if isinstance(provider, ProviderCapability):
            provider_rows[provider.provider_id] = _provider_contract_row(provider)

    # Ensure Spotify exists in providers even if not listed externally.
    spotify = getattr(capabilities, "spotify", None)
    if "spotify" not in provider_rows and spotify is not None:
        provider_rows["spotify"] = {
            "provider_id": "spotify",
            "display_name": "Spotify",
            "required": False,
            "optional": True,
            "listed": True,
            "enabled": True,
            "installed": bool(spotify.addon_available),
            "addon_available": bool(spotify.addon_available),
            "configured": bool(spotify.configured),
            "auth_required": True,
            "auth_state": "authenticated" if spotify.configured else "unauthenticated",
            "readiness": "ready" if spotify.configured else "degraded",
            "degraded_reasons": [] if spotify.configured else ["unauthenticated"],
            "status_message": spotify.status_message,
            "action_label": spotify.action_label,
            "supported_capabilities": _provider_supported_capabilities("spotify"),
            "can_skip_setup": True,
            "can_retry_setup": True,
            "next_actions": [
                "Run `dplayer auth spotify-doctor`.",
                "Run `dplayer auth spotify --open-browser`.",
            ],
            "docs_url": _SPOTIFY_OAUTH_GUIDE_URL,
            "experimental": False,
            "experimental_flag": None,
        }

    providers = list(provider_rows.values())
    ready_provider_count = sum(1 for row in providers if row.get("readiness") == "ready")
    optional_provider_count = len(providers)
    any_provider_ready = ready_provider_count > 0

    if not discogs_configured:
        onboarding_state = "needs_required_setup"
    elif collection_synced is False:
        onboarding_state = "needs_initial_sync"
    elif optional_provider_count > 0 and not any_provider_ready:
        onboarding_state = "core_ready_optional_pending"
    else:
        onboarding_state = "ready"

    next_actions: list[str] = []
    if not discogs_configured:
        next_actions.extend(_discogs_contract_row(discogs_configured=False)["next_actions"])
    if optional_provider_count > 0 and not any_provider_ready:
        for row in providers:
            if row.get("readiness") == "ready":
                continue
            row_actions = row.get("next_actions")
            if isinstance(row_actions, list):
                for action in row_actions:
                    text = str(action).strip()
                    if text:
                        next_actions.append(text)
    # De-dupe while preserving order.
    next_actions = list(dict.fromkeys(next_actions))

    return {
        "schema_version": 1,
        "core_service": _discogs_contract_row(discogs_configured=bool(discogs_configured)),
        "providers": providers,
        "summary": {
            "required_services_configured": bool(discogs_configured),
            "optional_provider_count": optional_provider_count,
            "ready_provider_count": ready_provider_count,
            "degraded_mode": bool(optional_provider_count > 0 and not any_provider_ready),
            "onboarding_state": onboarding_state,
            "collection_synced": collection_synced,
            "next_actions": next_actions,
            "can_skip_optional_setup": True,
        },
    }
