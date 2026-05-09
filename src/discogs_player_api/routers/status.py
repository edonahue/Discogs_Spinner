"""Status and capability routes."""

from __future__ import annotations

from fastapi import APIRouter, Query

from discogs_player.capabilities import get_capabilities
from discogs_player.use_cases.collection_analytics import run_collection_analytics
from discogs_player.use_cases.provider_readiness import (
    build_provider_readiness_contract,
)
from discogs_player.use_cases.status_report import get_status_report
from discogs_player_api.runtime import run_use_case

router = APIRouter(tags=["status"])


@router.get("/status")
def api_status() -> dict[str, object]:
    return run_use_case(get_status_report)


@router.get("/analytics")
def api_analytics(
    limit: int = Query(default=10, ge=1),
) -> dict[str, object]:
    return run_use_case(lambda: run_collection_analytics(limit=limit))


@router.get("/capabilities")
def api_capabilities() -> dict[str, object]:
    def _payload() -> dict[str, object]:
        capabilities = get_capabilities()
        spotify = capabilities.spotify

        payload: dict[str, object] = {
            "spotify": {
                "addon_available": spotify.addon_available,
                "configured": spotify.configured,
                "action_label": spotify.action_label,
                "status_message": spotify.status_message,
            }
        }
        providers: list[dict[str, object]] = []
        for provider in getattr(capabilities, "providers", ()):
            providers.append(
                {
                    "provider_id": provider.provider_id,
                    "display_name": provider.display_name,
                    "listed": provider.listed,
                    "enabled": provider.enabled,
                    "importable": provider.importable,
                    "addon_available": provider.addon_available,
                    "configured": provider.configured,
                    "action_label": provider.action_label,
                    "status_message": provider.status_message,
                    "docs_url": provider.docs_url,
                    "experimental": provider.experimental,
                    "experimental_flag": provider.experimental_flag,
                }
            )
        if providers:
            payload["providers"] = providers
        payload["provider_readiness"] = build_provider_readiness_contract(
            app_capabilities=capabilities,
            collection_synced=None,
        )
        return payload

    return run_use_case(_payload)
