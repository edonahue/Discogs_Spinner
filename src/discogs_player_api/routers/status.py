"""Status and capability routes."""

from __future__ import annotations

from fastapi import APIRouter

from discogs_player.capabilities import get_capabilities
from discogs_player.use_cases.status_report import get_status_report
from discogs_player_api.runtime import run_use_case

router = APIRouter(tags=["status"])


@router.get("/status")
def api_status() -> dict[str, object]:
    return run_use_case(get_status_report)


@router.get("/capabilities")
def api_capabilities() -> dict[str, object]:
    def _payload() -> dict[str, object]:
        spotify = get_capabilities().spotify
        return {
            "spotify": {
                "addon_available": spotify.addon_available,
                "configured": spotify.configured,
                "action_label": spotify.action_label,
                "status_message": spotify.status_message,
            }
        }

    return run_use_case(_payload)
