"""Playback routes."""

from __future__ import annotations

from fastapi import APIRouter

from discogs_player.use_cases.play_release import run_play_release
from discogs_player_api.models import PlayRequest
from discogs_player_api.runtime import run_use_case

router = APIRouter(tags=["playback"])


@router.post("/play/{discogs_release_id}")
def api_play_release(
    discogs_release_id: int,
    request: PlayRequest,
) -> dict[str, object]:
    return run_use_case(
        lambda: run_play_release(
            discogs_release_id=discogs_release_id,
            auto_match=bool(request.auto_match),
            open_fallback=bool(request.open_fallback),
        )
    )


@router.post("/play/last-spin")
def api_play_last_spin(request: PlayRequest) -> dict[str, object]:
    return run_use_case(
        lambda: run_play_release(
            use_last_spin=True,
            auto_match=bool(request.auto_match),
            open_fallback=bool(request.open_fallback),
        )
    )
