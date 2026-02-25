"""Capture a point-in-time market value snapshot for trend tracking."""

from __future__ import annotations

from datetime import datetime, timezone

from discogs_player.data.db import get_connection
from discogs_player.data.repo import (
    get_market_value_summary,
    insert_market_value_snapshot,
)


def run_market_value_snapshot() -> dict[str, object]:
    captured_at = datetime.now(timezone.utc).isoformat()

    conn = get_connection()
    try:
        summary = get_market_value_summary(conn)
        snapshot_id = insert_market_value_snapshot(
            conn,
            captured_at=captured_at,
            active_release_count=int(summary.get("active_release_count") or 0),
            priced_release_count=int(summary.get("priced_release_count") or 0),
            unpriced_release_count=int(summary.get("unpriced_release_count") or 0),
            total_lowest=float(summary.get("total_lowest") or 0.0),
            total_median=float(summary.get("total_median") or 0.0),
            total_highest=float(summary.get("total_highest") or 0.0),
        )
    finally:
        conn.close()

    return {
        "snapshot_id": snapshot_id,
        "captured_at": captured_at,
        "active_release_count": int(summary.get("active_release_count") or 0),
        "priced_release_count": int(summary.get("priced_release_count") or 0),
        "unpriced_release_count": int(summary.get("unpriced_release_count") or 0),
        "total_lowest": float(summary.get("total_lowest") or 0.0),
        "total_median": float(summary.get("total_median") or 0.0),
        "total_highest": float(summary.get("total_highest") or 0.0),
        "market_value_last_updated": summary.get("market_value_last_updated"),
        "currency_counts": list(summary.get("currency_counts") or []),
    }
