"""Sync operation routes."""

from __future__ import annotations

from fastapi import APIRouter

from discogs_player.use_cases.sync_collection import run_sync_collection
from discogs_player.use_cases.sync_wantlist import run_sync_wantlist
from discogs_player_api.models import SyncRequest
from discogs_player_api.runtime import run_use_case

router = APIRouter(tags=["sync"])


@router.post("/sync/collection")
def api_sync_collection(request: SyncRequest) -> dict[str, object]:
    return run_use_case(
        lambda: run_sync_collection(
            allow_empty_deactivate=bool(request.allow_empty_deactivate),
        )
    )


@router.post("/sync/wantlist")
def api_sync_wantlist(request: SyncRequest) -> dict[str, object]:
    return run_use_case(
        lambda: run_sync_wantlist(
            allow_empty_deactivate=bool(request.allow_empty_deactivate),
        )
    )
