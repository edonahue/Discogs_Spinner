"""Runtime performance profile helpers.

The defaults are intentionally conservative for the desktop UI: the app should
paint quickly and stay quiet instead of saturating the machine with preload work.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class PerformanceProfile:
    name: str
    cover_workers: int
    carousel_prefetch_inflight: int
    carousel_lookahead: int
    carousel_backtrack: int
    carousel_texture_cache: int
    gallery_initial_items: int
    gallery_chunk_items: int


_PROFILES: dict[str, PerformanceProfile] = {
    "game": PerformanceProfile(
        name="game",
        cover_workers=1,
        carousel_prefetch_inflight=0,
        carousel_lookahead=0,
        carousel_backtrack=0,
        carousel_texture_cache=16,
        gallery_initial_items=24,
        gallery_chunk_items=16,
    ),
    "quiet": PerformanceProfile(
        name="quiet",
        cover_workers=2,
        carousel_prefetch_inflight=4,
        carousel_lookahead=6,
        carousel_backtrack=2,
        carousel_texture_cache=32,
        gallery_initial_items=48,
        gallery_chunk_items=32,
    ),
    "balanced": PerformanceProfile(
        name="balanced",
        cover_workers=4,
        carousel_prefetch_inflight=8,
        carousel_lookahead=12,
        carousel_backtrack=4,
        carousel_texture_cache=64,
        gallery_initial_items=72,
        gallery_chunk_items=48,
    ),
    "fast": PerformanceProfile(
        name="fast",
        cover_workers=8,
        carousel_prefetch_inflight=16,
        carousel_lookahead=24,
        carousel_backtrack=6,
        carousel_texture_cache=96,
        gallery_initial_items=120,
        gallery_chunk_items=80,
    ),
}


def _positive_env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return int(default)
    try:
        parsed = int(str(raw).strip())
    except ValueError:
        return int(default)
    return parsed if parsed > 0 else int(default)


def _nonnegative_env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return int(default)
    try:
        parsed = int(str(raw).strip())
    except ValueError:
        return int(default)
    return parsed if parsed >= 0 else int(default)


def performance_profile() -> PerformanceProfile:
    requested = os.environ.get("DP_PERF_PROFILE", "balanced").strip().casefold()
    base = _PROFILES.get(requested, _PROFILES["balanced"])
    cpu_count = os.cpu_count() or 4
    cover_workers = min(
        max(1, cpu_count),
        _positive_env_int("DP_COVER_WORKERS", base.cover_workers),
    )
    return PerformanceProfile(
        name=base.name,
        cover_workers=cover_workers,
        carousel_prefetch_inflight=_nonnegative_env_int(
            "DP_CAROUSEL_PREFETCH_INFLIGHT",
            base.carousel_prefetch_inflight,
        ),
        carousel_lookahead=_nonnegative_env_int(
            "DP_CAROUSEL_LOOKAHEAD",
            base.carousel_lookahead,
        ),
        carousel_backtrack=_nonnegative_env_int(
            "DP_CAROUSEL_BACKTRACK",
            base.carousel_backtrack,
        ),
        carousel_texture_cache=_positive_env_int(
            "DP_CAROUSEL_TEXTURE_CACHE",
            base.carousel_texture_cache,
        ),
        gallery_initial_items=_positive_env_int(
            "DP_GALLERY_INITIAL_ITEMS",
            base.gallery_initial_items,
        ),
        gallery_chunk_items=_positive_env_int(
            "DP_GALLERY_CHUNK_ITEMS",
            base.gallery_chunk_items,
        ),
    )


def cover_worker_count() -> int:
    return performance_profile().cover_workers
