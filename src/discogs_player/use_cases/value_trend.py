"""Read market value snapshot history and derive trend deltas."""

from __future__ import annotations

from discogs_player.data.db import get_connection
from discogs_player.data.repo import query_market_value_snapshots


def run_market_value_trend(*, limit: int = 30) -> dict[str, object]:
    if limit < 1:
        raise ValueError("limit must be >= 1")

    conn = get_connection()
    try:
        # Query descending for index efficiency, then render chronologically.
        points_desc = query_market_value_snapshots(conn, limit=limit)
    finally:
        conn.close()

    points = list(reversed(points_desc))
    previous_median: float | None = None
    for item in points:
        current_median = float(item.get("total_median") or 0.0)
        if previous_median is None:
            item["delta_total_median"] = None
            item["delta_total_median_percent"] = None
        else:
            delta = current_median - previous_median
            item["delta_total_median"] = delta
            item["delta_total_median_percent"] = (
                (delta / previous_median * 100.0) if previous_median != 0.0 else None
            )
        previous_median = current_median

    if not points:
        return {
            "snapshot_count": 0,
            "window_start": None,
            "window_end": None,
            "window_delta_total_median": None,
            "window_delta_total_median_percent": None,
            "points": [],
        }

    first = points[0]
    last = points[-1]
    first_median = float(first.get("total_median") or 0.0)
    last_median = float(last.get("total_median") or 0.0)
    window_delta = last_median - first_median
    window_delta_percent = (window_delta / first_median * 100.0) if first_median != 0.0 else None

    return {
        "snapshot_count": len(points),
        "window_start": first.get("captured_at"),
        "window_end": last.get("captured_at"),
        "window_delta_total_median": window_delta,
        "window_delta_total_median_percent": window_delta_percent,
        "points": points,
    }
