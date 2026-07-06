from __future__ import annotations

import csv
import json

import pytest

from discogs_player.core.settings import set_setting
from discogs_player.data.db import get_connection
from discogs_player.data.repo import upsert_market_price, upsert_releases
from discogs_player.use_cases.export_collection import run_export_collection


def _release(
    release_id: int,
    *,
    is_active: int = 1,
    has_lp: bool | None = None,
    has_45: bool | None = None,
) -> dict[str, object]:
    return {
        "discogs_release_id": release_id,
        "artist": "Artist",
        "title": f"Album {release_id}",
        "year": 2001,
        "genres": ["Rock"],
        "styles": ["Alt"],
        "thumb_url": None,
        "cover_url": None,
        "added_at": "2026-01-01T00:00:00Z",
        "last_synced_at": "2026-01-01T00:00:00Z",
        "has_lp": has_lp,
        "has_45": has_45,
        "is_active": is_active,
    }


def test_export_collection_json_snapshot(isolated_xdg, tmp_path):
    conn = get_connection()
    try:
        upsert_releases(conn, [_release(11), _release(22, is_active=0)])
        conn.execute(
            """
            INSERT INTO spotify_mapping(discogs_release_id, spotify_album_id, confidence, last_checked_at, is_override)
            VALUES (?, ?, ?, ?, ?)
            """,
            (11, "album-11", 0.88, "2026-01-03T00:00:00Z", 0),
        )
        upsert_market_price(
            conn,
            discogs_release_id=11,
            lowest=12.5,
            median=17.0,
            highest=22.25,
            currency="USD",
            last_updated_at="2026-02-07T00:00:00+00:00",
        )
        set_setting("last_sync_time", "2026-02-07T00:00:00+00:00", conn=conn)
        set_setting("discogs_token", "secret-token", conn=conn)
        set_setting("spotify_refresh_token", "secret-refresh-token", conn=conn)
    finally:
        conn.close()

    output = tmp_path / "backup.json"
    result = run_export_collection(
        output_path=str(output), export_format="json", include_inactive=True
    )

    assert result["ok"] is True
    assert result["export_format"] == "json"
    assert result["release_count"] == 2
    assert output.exists()

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["release_count"] == 2
    assert payload["include_inactive"] is True
    assert payload["settings"]["last_sync_time"] == "2026-02-07T00:00:00+00:00"
    assert payload["settings"]["discogs_token"] == "<redacted>"
    assert payload["settings"]["spotify_refresh_token"] == "<redacted>"
    assert payload["attribution"] == {
        "text": "Data provided by Discogs",
        "url": "https://www.discogs.com/",
    }

    releases = payload["releases"]
    release_11 = next(item for item in releases if item["discogs_release_id"] == 11)
    assert release_11["has_lp"] is None
    assert release_11["has_45"] is None
    assert release_11["spotify_album_id"] == "album-11"
    assert release_11["spotify_confidence"] == 0.88
    assert release_11["spotify_is_override"] is False
    assert release_11["market_lowest"] == 12.5
    assert release_11["market_median"] == 17.0
    assert release_11["market_highest"] == 22.25
    assert release_11["market_currency"] == "USD"
    assert release_11["market_last_updated_at"] == "2026-02-07T00:00:00+00:00"


def test_export_collection_csv_active_only(isolated_xdg, tmp_path):
    conn = get_connection()
    try:
        upsert_releases(
            conn,
            [_release(1, has_lp=True, has_45=False), _release(2, is_active=0)],
        )
    finally:
        conn.close()

    output = tmp_path / "backup.csv"
    result = run_export_collection(
        output_path=str(output), export_format="csv", include_inactive=False
    )

    assert result["export_format"] == "csv"
    assert result["release_count"] == 1

    with output.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 1
    assert rows[0]["discogs_release_id"] == "1"
    assert rows[0]["is_active"] == "1"
    assert rows[0]["has_lp"] == "1"
    assert rows[0]["has_45"] == "0"
    assert rows[0]["genres"] == '["Rock"]'
    assert rows[0]["market_lowest"] == ""
    assert rows[0]["market_currency"] == ""
    assert rows[0]["data_source"] == "Data provided by Discogs"
    assert rows[0]["data_source_url"] == "https://www.discogs.com/"


def test_export_collection_rejects_invalid_format(isolated_xdg, tmp_path):
    output = tmp_path / "backup.invalid"
    with pytest.raises(ValueError, match="Export format must be 'json' or 'csv'"):
        run_export_collection(output_path=str(output), export_format="yaml")
