"""Provider readiness contract for setup/status/onboarding surfaces."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

from discogs_player.capabilities import AppCapabilities, ProviderCapability, get_capabilities
from discogs_player.core.settings import get_discogs_token
from discogs_player.integrations.provider_registry import provider_descriptor

_SPOTIFY_DASHBOARD_URL = "https://developer.spotify.com/dashboard"
_SPOTIFY_OAUTH_GUIDE_URL = (
    "https://developer.spotify.com/documentation/web-api/tutorials/code-flow"
)
_DISCOGS_TOKEN_URL = "https://www.discogs.com/settings/developers"


def _provider_auth_required(provider: ProviderCapability, descriptor: dict[str, Any]) -> bool:
    raw = descriptor.get("auth_required")
    if isinstance(raw, bool):
        return raw
    return provider.provider_id == "spotify"


def _provider_supported_capabilities(descriptor: dict[str, Any]) -> list[str]:
    raw = descriptor.get("supported_capabilities")
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    return []


def _provider_next_actions(
    provider: ProviderCapability,
    *,
    descriptor: dict[str, Any],
    auth_required: bool,
) -> list[str]:
    if not provider.enabled and provider.experimental_flag:
        return [f"Set {provider.experimental_flag}=1 to enable provider scaffolding."]
    if not provider.importable:
        return ["Install provider dependencies before enabling this provider."]
    if not provider.addon_available:
        return ["Install optional addon dependencies for this provider."]
    if auth_required and not provider.configured:
        configured_actions = descriptor.get("next_actions_when_unconfigured")
        actions: list[str] = []
        if isinstance(configured_actions, list):
            actions.extend(str(item).strip() for item in configured_actions if str(item).strip())
        setup_url = str(descriptor.get("setup_url") or "").strip()
        oauth_url = str(descriptor.get("oauth_guide_url") or "").strip()
        if setup_url:
            actions.append(f"Setup: {setup_url}")
        if oauth_url:
            actions.append(f"Guide: {oauth_url}")
        if actions:
            return list(dict.fromkeys(actions))
        return [
            "Run provider auth/setup flow.",
        ]
    if not provider.configured:
        configured_actions = descriptor.get("next_actions_when_unconfigured")
        if isinstance(configured_actions, list):
            actions = [str(item).strip() for item in configured_actions if str(item).strip()]
            if actions:
                return list(dict.fromkeys(actions))
        return ["Run provider auth/setup flow."]
    return ["Provider is ready for playback and matching."]


def _provider_degraded_reasons(
    provider: ProviderCapability,
    *,
    auth_required: bool,
) -> list[str]:
    reasons: list[str] = []
    if not provider.enabled:
        reasons.append("disabled")
    if not provider.importable:
        reasons.append("backend_not_installed")
    if provider.importable and not provider.addon_available:
        reasons.append("addon_unavailable")
    if provider.addon_available and auth_required and not provider.configured:
        reasons.append("unauthenticated")
    if provider.addon_available and not auth_required and not provider.configured:
        reasons.append("not_configured")
    return reasons


def _provider_readiness(provider: ProviderCapability, *, auth_required: bool) -> str:
    reasons = _provider_degraded_reasons(provider, auth_required=auth_required)
    if not reasons and provider.configured:
        return "ready"
    if not provider.importable or not provider.addon_available:
        return "unavailable"
    return "degraded"


def _provider_contract_row(provider: ProviderCapability) -> dict[str, object]:
    descriptor = provider_descriptor(provider.provider_id)
    auth_required = _provider_auth_required(provider, descriptor)
    readiness = _provider_readiness(provider, auth_required=auth_required)
    degraded_reasons = _provider_degraded_reasons(provider, auth_required=auth_required)
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
        "supported_capabilities": _provider_supported_capabilities(descriptor),
        "can_skip_setup": bool(descriptor.get("can_skip_setup", True)),
        "can_retry_setup": bool(
            descriptor.get(
                "can_retry_setup",
                bool(not provider.configured or not provider.addon_available),
            )
        ),
        "next_actions": _provider_next_actions(
            provider,
            descriptor=descriptor,
            auth_required=auth_required,
        ),
        "docs_url": provider.docs_url,
        "setup_url": str(descriptor.get("setup_url") or "") or None,
        "oauth_guide_url": str(descriptor.get("oauth_guide_url") or "") or None,
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
        descriptor = provider_descriptor("spotify")
        supported_capabilities = _provider_supported_capabilities(descriptor)
        next_actions = descriptor.get("next_actions_when_unconfigured")
        if not isinstance(next_actions, list):
            next_actions = [
                "Run `dplayer auth spotify-doctor`.",
                "Run `dplayer auth spotify --open-browser`.",
            ]
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
            "supported_capabilities": supported_capabilities,
            "can_skip_setup": True,
            "can_retry_setup": True,
            "next_actions": [
                str(item).strip() for item in next_actions if str(item).strip()
            ],
            "docs_url": str(descriptor.get("setup_url") or _SPOTIFY_DASHBOARD_URL),
            "setup_url": str(descriptor.get("setup_url") or _SPOTIFY_DASHBOARD_URL),
            "oauth_guide_url": str(
                descriptor.get("oauth_guide_url") or _SPOTIFY_OAUTH_GUIDE_URL
            ),
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
        "schema_version": 2,
        "core_service": _discogs_contract_row(discogs_configured=bool(discogs_configured)),
        "providers": providers,
        "next_actions": next_actions,
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
