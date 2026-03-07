"""Prioritize market price refresh candidates by value impact.

Priority order:
  1. missing  — no market_prices row exists at all
  2. unpriced — row exists but all price fields are NULL
  3. stale    — prices exist but older than stale_days
               within stale: sorted by current median descending (high-value first)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from discogs_player.data.db import get_connection
from discogs_player.data.repo import query_releases_needing_market_refresh

_PRIORITY: dict[str, int] = {
    "missing": 0,
    "unpriced": 1,
    "stale": 2,
    "unknown": 3,
}


def _sort_key(item: dict[str, object]) -> tuple[int, float, str]:
    tier = _PRIORITY.get(str(item.get("market_need_reason") or "unknown"), 3)
    median_raw = item.get("market_median")
    median = float(median_raw) if isinstance(median_raw, (int, float)) else 0.0
    artist = str(item.get("artist") or "").lower()
    return (tier, -median, artist)


def run_value_refresh_queue(
    *,
    limit: int = 25,
    stale_days: int = 30,
) -> dict[str, object]:
    """Return a prioritized refresh queue for market price candidates.

    Args:
        limit: Maximum number of entries to return in the queue.
        stale_days: Treat market prices older than this as stale.

    Returns:
        Dict with total_candidates, counts by reason, stale_days, limit,
        and a ``queue`` list ordered by priority then value descending.
    """
    if limit < 1:
        raise ValueError("limit must be >= 1")
    if stale_days < 0:
        raise ValueError("stale_days must be >= 0")

    stale_before = (
        datetime.now(timezone.utc) - timedelta(days=stale_days)
    ).isoformat()

    conn = get_connection()
    try:
        candidates = query_releases_needing_market_refresh(
            conn,
            limit=None,
            stale_before=stale_before,
            include_market=True,
        )
    finally:
        conn.close()

    sorted_candidates = sorted(candidates, key=_sort_key)

    counts: dict[str, int] = {"missing": 0, "unpriced": 0, "stale": 0}
    for item in candidates:
        reason = str(item.get("market_need_reason") or "unknown")
        if reason in counts:
            counts[reason] += 1

    return {
        "total_candidates": len(candidates),
        "missing_count": counts["missing"],
        "unpriced_count": counts["unpriced"],
        "stale_count": counts["stale"],
        "stale_days": stale_days,
        "limit": limit,
        "queue": sorted_candidates[:limit],
    }
