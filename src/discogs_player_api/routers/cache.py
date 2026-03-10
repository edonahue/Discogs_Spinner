"""Cover image cache management routes."""

from __future__ import annotations

from fastapi import APIRouter, Query

from discogs_player.use_cases.cover_cache import (
    run_cover_cache_prune,
    run_cover_cache_stats,
    run_cover_cache_warm,
)
from discogs_player_api.runtime import run_use_case

router = APIRouter(tags=["cache"])


@router.get("/cache/stats")
def api_cache_stats() -> dict[str, object]:
    """Return cover image cache stats (item count, disk usage, oldest/newest entry)."""
    return run_use_case(run_cover_cache_stats)


@router.post("/cache/prune")
def api_cache_prune(
    days: int = Query(default=30, ge=1),
) -> dict[str, object]:
    """Delete cover cache entries older than ``days`` days."""
    return run_use_case(lambda: run_cover_cache_prune(days=days))


@router.post("/cache/warm")
def api_cache_warm(
    limit: int | None = Query(default=None, ge=1),
) -> dict[str, object]:
    """Pre-fetch missing cover images for active collection releases."""
    return run_use_case(lambda: run_cover_cache_warm(limit=limit))
