"""Setup and onboarding routes."""

from __future__ import annotations

from fastapi import APIRouter

from discogs_player.use_cases.config_management import run_config_set
from discogs_player.use_cases.setup_report import run_setup_report
from discogs_player_api.models import SetupRequest
from discogs_player_api.runtime import run_use_case

router = APIRouter(tags=["setup"])


@router.get("/setup")
def api_get_setup() -> dict[str, object]:
    return run_use_case(run_setup_report)


@router.post("/setup")
def api_post_setup(request: SetupRequest) -> dict[str, object]:
    def _save_and_report() -> dict[str, object]:
        run_config_set("discogs_token", request.discogs_token)
        return run_setup_report()

    return run_use_case(_save_and_report)
