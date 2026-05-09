"""Sync operation routes."""

from __future__ import annotations

from collections.abc import Callable
from threading import Lock
from typing import TypeVar

from fastapi import APIRouter, HTTPException

from discogs_player.use_cases.sync_collection import run_sync_collection
from discogs_player.use_cases.sync_wantlist import run_sync_wantlist
from discogs_player_api.models import SyncRequest
from discogs_player_api.runtime import run_use_case

router = APIRouter(tags=["sync"])
T = TypeVar("T")
_sync_lock = Lock()


def _run_exclusive_sync(call: Callable[[], T]) -> dict[str, object]:
    if not _sync_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "sync_already_running",
                "message": "A sync operation is already running.",
                "retryable": True,
                "details": None,
            },
        )
    try:
        return run_use_case(call)
    finally:
        _sync_lock.release()


@router.post("/sync/collection")
def api_sync_collection(request: SyncRequest) -> dict[str, object]:
    return _run_exclusive_sync(
        lambda: run_sync_collection(
            allow_empty_deactivate=bool(request.allow_empty_deactivate),
        )
    )


@router.post("/sync/wantlist")
def api_sync_wantlist(request: SyncRequest) -> dict[str, object]:
    return _run_exclusive_sync(
        lambda: run_sync_wantlist(
            allow_empty_deactivate=bool(request.allow_empty_deactivate),
        )
    )
