"""Market value routes."""

from __future__ import annotations

from threading import Lock

from fastapi import APIRouter, HTTPException, Query

from discogs_player.use_cases.collection_health import run_collection_health
from discogs_player.use_cases.hidden_gems import run_hidden_gems
from discogs_player.use_cases.value_dashboard import run_market_value_dashboard
from discogs_player.use_cases.value_refresh import run_refresh_market_values
from discogs_player.use_cases.value_refresh_queue import run_value_refresh_queue
from discogs_player.use_cases.value_snapshot import run_market_value_snapshot
from discogs_player.use_cases.value_status import run_market_value_status
from discogs_player_api.models import ValueRefreshRequest
from discogs_player_api.runtime import run_use_case

router = APIRouter(tags=["value"])
_value_refresh_lock = Lock()


@router.get("/value/status")
def api_market_value_status() -> dict[str, object]:
    return run_use_case(run_market_value_status)


@router.get("/value/dashboard")
def api_market_value_dashboard(
    top_limit: int = Query(default=10, ge=1),
    bottom_limit: int = Query(default=2, ge=1),
    trend_limit: int = Query(default=12, ge=1),
    detector_limit: int = Query(default=8, ge=1),
) -> dict[str, object]:
    return run_use_case(
        lambda: run_market_value_dashboard(
            top_limit=int(top_limit),
            bottom_limit=int(bottom_limit),
            trend_limit=int(trend_limit),
            detector_limit=int(detector_limit),
        )
    )


@router.post("/value/refresh")
def api_market_value_refresh(request: ValueRefreshRequest) -> dict[str, object]:
    if not _value_refresh_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "value_refresh_already_running",
                "message": "A market value refresh is already running.",
                "retryable": True,
                "details": None,
            },
        )
    try:
        return run_use_case(
            lambda: run_refresh_market_values(
                limit=int(request.limit),
                stale_days=int(request.stale_days),
                release_ids=request.release_ids,
                from_missing=bool(request.from_missing),
            )
        )
    finally:
        _value_refresh_lock.release()


@router.post("/value/snapshot")
def api_market_value_snapshot() -> dict[str, object]:
    return run_use_case(run_market_value_snapshot)


@router.get("/value/queue")
def api_value_refresh_queue(
    limit: int = Query(default=25, ge=1),
    stale_days: int = Query(default=30, ge=0),
) -> dict[str, object]:
    return run_use_case(
        lambda: run_value_refresh_queue(limit=limit, stale_days=stale_days)
    )


@router.get("/value/health")
def api_collection_health() -> dict[str, object]:
    return run_use_case(run_collection_health)


@router.get("/value/gems")
def api_hidden_gems(
    min_median: float = Query(default=25.0, ge=0.0),
    limit: int = Query(default=25, ge=1),
) -> dict[str, object]:
    return run_use_case(
        lambda: run_hidden_gems(min_median=float(min_median), limit=int(limit))
    )
