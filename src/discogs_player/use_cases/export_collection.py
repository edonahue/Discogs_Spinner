"""Export local collection and settings snapshots for backup portability."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from discogs_player.core.settings import list_settings
from discogs_player.data.db import LATEST_SCHEMA_VERSION, get_connection
from discogs_player.data.repo import get_release_counts, query_releases_for_export

CSV_COLUMNS: tuple[str, ...] = (
    "discogs_release_id",
    "artist",
    "title",
    "year",
    "genres",
    "styles",
    "thumb_url",
    "cover_url",
    "added_at",
    "last_synced_at",
    "has_lp",
    "has_45",
    "is_active",
    "spotify_album_id",
    "spotify_confidence",
    "spotify_last_checked_at",
    "spotify_is_override",
    "market_lowest",
    "market_median",
    "market_highest",
    "market_currency",
    "market_last_updated_at",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_export_format(raw: str) -> str:
    fmt = raw.strip().lower()
    if fmt not in {"json", "csv"}:
        raise ValueError("Export format must be 'json' or 'csv'.")
    return fmt


def _serialize_csv_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=True, sort_keys=True)
    return str(value)


def _as_dict_list(value: object | None) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, object]] = []
    for item in value:
        if isinstance(item, dict):
            rows.append(item)
    return rows


def build_export_payload(*, include_inactive: bool = True) -> dict[str, object]:
    conn = get_connection()
    try:
        releases = query_releases_for_export(conn, include_inactive=include_inactive)
        counts = get_release_counts(conn)
        settings = list_settings(conn=conn)
    finally:
        conn.close()

    return {
        "generated_at": _now_iso(),
        "schema_version": LATEST_SCHEMA_VERSION,
        "include_inactive": include_inactive,
        "counts": counts,
        "settings": settings,
        "release_count": len(releases),
        "releases": releases,
    }


def run_export_collection(
    *,
    output_path: str,
    export_format: str = "json",
    include_inactive: bool = True,
) -> dict[str, object]:
    normalized_format = _normalize_export_format(export_format)
    output = Path(output_path).expanduser()
    if output.exists() and output.is_dir():
        raise ValueError(f"Output path is a directory: {output}")

    output.parent.mkdir(parents=True, exist_ok=True)
    payload = build_export_payload(include_inactive=include_inactive)
    releases = _as_dict_list(payload.get("releases"))

    if normalized_format == "json":
        output.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    else:
        with output.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            for item in releases:
                writer.writerow(
                    {key: _serialize_csv_value(item.get(key)) for key in CSV_COLUMNS}
                )

    return {
        "ok": True,
        "export_format": normalized_format,
        "output_path": str(output),
        "include_inactive": include_inactive,
        "release_count": len(releases),
    }
