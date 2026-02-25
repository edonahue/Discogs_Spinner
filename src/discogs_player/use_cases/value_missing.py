"""List active releases that still lack cached market value data."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any
from datetime import datetime, timedelta, timezone

from discogs_player.data.db import get_connection
from discogs_player.data.repo import query_releases_needing_market_refresh

CSV_COLUMNS: tuple[str, ...] = (
    "discogs_release_id",
    "artist",
    "title",
    "year",
    "is_active",
    "spotify_album_id",
    "market_need_reason",
    "market_lowest",
    "market_median",
    "market_highest",
    "market_currency",
    "market_last_updated_at",
)


def _serialize_csv_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "1" if value else "0"
    return str(value)


def run_market_value_missing(
    *,
    limit: int = 25,
    stale_days: int | None = None,
    with_value: bool = False,
) -> list[dict[str, object]]:
    if limit < 1:
        raise ValueError("limit must be >= 1")
    if stale_days is not None and stale_days < 0:
        raise ValueError("stale_days must be >= 0")

    stale_before: str | None = None
    if stale_days is not None:
        stale_before = (
            datetime.now(timezone.utc) - timedelta(days=int(stale_days))
        ).isoformat()

    conn = get_connection()
    try:
        return query_releases_needing_market_refresh(
            conn,
            limit=limit,
            stale_before=stale_before,
            include_market=with_value,
        )
    finally:
        conn.close()


def write_market_value_missing_csv(
    *,
    releases: list[dict[str, object]],
    output_path: str,
) -> dict[str, object]:
    output = Path(output_path).expanduser()
    if output.exists() and output.is_dir():
        raise ValueError(f"Output path is a directory: {output}")

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for item in releases:
            writer.writerow(
                {key: _serialize_csv_value(item.get(key)) for key in CSV_COLUMNS}
            )

    return {
        "ok": True,
        "output_path": str(output),
        "row_count": len(releases),
    }
