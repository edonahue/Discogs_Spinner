from __future__ import annotations

import json

import pytest

from discogs_player.core.settings import get_setting, set_setting
from discogs_player.data.db import LATEST_SCHEMA_VERSION, get_connection
from discogs_player.data.repo import (
    get_market_price,
    get_release_by_id,
    get_release_counts,
    get_spotify_mapping,
    upsert_market_price,
    upsert_releases,
)
from discogs_player.use_cases.import_collection import run_import_collection


def _release(release_id: int, *, artist: str = "Artist", title: str = "Album") -> dict[str, object]:
    return {
        "discogs_release_id": release_id,
        "artist": artist,
        "title": title,
        "year": 2001,
        "genres": ["Rock"],
        "styles": ["Alt"],
        "thumb_url": None,
        "cover_url": None,
        "added_at": "2026-01-01T00:00:00Z",
        "last_synced_at": "2026-01-01T00:00:00Z",
        "is_active": 1,
    }


def _write_payload(path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_import_collection_merge_updates_and_adds(isolated_xdg, tmp_path):
    conn = get_connection()
    try:
        upsert_releases(conn, [_release(9, artist="Existing", title="Old")])
        set_setting("import_key", "old-value", conn=conn)
    finally:
        conn.close()

    payload = {
        "schema_version": LATEST_SCHEMA_VERSION,
        "release_count": 2,
        "settings": {"import_key": "new-value", "fresh_key": "abc"},
        "releases": [
            {
                **_release(1, artist="Nirvana", title="Nevermind"),
                "spotify_album_id": "spotify:album:1",
                "spotify_confidence": 0.9,
                "spotify_last_checked_at": "2026-02-07T00:00:00Z",
                "spotify_is_override": False,
                "market_lowest": 10.0,
                "market_median": 12.5,
                "market_highest": 16.0,
                "market_currency": "USD",
                "market_last_updated_at": "2026-02-07T00:00:00+00:00",
            },
            _release(2, artist="Miles Davis", title="Kind of Blue"),
        ],
    }
    input_path = tmp_path / "import.json"
    _write_payload(input_path, payload)

    result = run_import_collection(input_path=str(input_path), conflict_mode="merge")

    assert result["ok"] is True
    assert result["conflict_mode"] == "merge"
    assert result["imported_release_count"] == 2
    assert result["imported_mapping_count"] == 1
    assert result["imported_market_price_count"] == 1
    assert result["imported_settings_count"] == 2

    conn = get_connection()
    try:
        counts = get_release_counts(conn)
        imported = get_release_by_id(conn, 1)
        existing = get_release_by_id(conn, 9)
        mapping = get_spotify_mapping(conn, 1)
        market_price = get_market_price(conn, 1)
    finally:
        conn.close()

    assert counts["release_count_total"] == 3
    assert imported is not None
    assert imported["artist"] == "Nirvana"
    assert existing is not None
    assert existing["artist"] == "Existing"
    assert mapping is not None
    assert mapping["spotify_album_id"] == "spotify:album:1"
    assert market_price is not None
    assert market_price["median"] == 12.5
    assert market_price["currency"] == "USD"
    assert get_setting("import_key") == "new-value"
    assert get_setting("fresh_key") == "abc"


def test_import_collection_replace_dry_run_does_not_modify_db(isolated_xdg, tmp_path):
    conn = get_connection()
    try:
        upsert_releases(conn, [_release(11, artist="Keep", title="Me")])
        set_setting("existing_key", "present", conn=conn)
    finally:
        conn.close()

    payload = {
        "schema_version": LATEST_SCHEMA_VERSION,
        "release_count": 1,
        "settings": {"existing_key": "changed"},
        "releases": [_release(22, artist="Dry", title="Run")],
    }
    input_path = tmp_path / "dry-run.json"
    _write_payload(input_path, payload)

    result = run_import_collection(
        input_path=str(input_path),
        conflict_mode="replace",
        dry_run=True,
        include_settings=True,
    )

    assert result["dry_run"] is True
    assert result["imported_release_count"] == 1
    assert result["imported_market_price_count"] == 0
    assert result["imported_settings_count"] == 1

    conn = get_connection()
    try:
        kept = get_release_by_id(conn, 11)
        new_release = get_release_by_id(conn, 22)
    finally:
        conn.close()

    assert kept is not None
    assert new_release is None
    assert get_setting("existing_key") == "present"


def test_import_collection_replace_replaces_data_and_settings(isolated_xdg, tmp_path):
    conn = get_connection()
    try:
        upsert_releases(conn, [_release(31, artist="Old", title="Record")])
        conn.execute(
            """
            INSERT INTO spotify_mapping(discogs_release_id, spotify_album_id, confidence, last_checked_at, is_override)
            VALUES (?, ?, ?, ?, ?)
            """,
            (31, "spotify:album:old", 0.6, "2026-01-01T00:00:00Z", 0),
        )
        upsert_market_price(
            conn,
            discogs_release_id=31,
            lowest=50.0,
            median=60.0,
            highest=80.0,
            currency="USD",
            last_updated_at="2026-01-01T00:00:00Z",
        )
        set_setting("old_key", "old-value", conn=conn)
        conn.commit()
    finally:
        conn.close()

    payload = {
        "schema_version": LATEST_SCHEMA_VERSION,
        "release_count": 1,
        "settings": {"new_key": "new-value"},
        "releases": [
            {
                **_release(41, artist="New", title="Record"),
                "spotify_album_id": "spotify:album:new",
                "spotify_confidence": 0.99,
                "spotify_last_checked_at": "2026-02-07T00:00:00Z",
                "spotify_is_override": True,
                "market_lowest": 14.0,
                "market_median": 18.0,
                "market_highest": 21.0,
                "market_currency": "EUR",
                "market_last_updated_at": "2026-02-07T00:00:00+00:00",
            }
        ],
    }
    input_path = tmp_path / "replace.json"
    _write_payload(input_path, payload)

    result = run_import_collection(
        input_path=str(input_path),
        conflict_mode="replace",
        dry_run=False,
        include_settings=True,
    )

    assert result["conflict_mode"] == "replace"
    assert result["imported_release_count"] == 1
    assert result["imported_mapping_count"] == 1
    assert result["imported_market_price_count"] == 1

    conn = get_connection()
    try:
        counts = get_release_counts(conn)
        old_release = get_release_by_id(conn, 31)
        new_release = get_release_by_id(conn, 41)
        new_mapping = get_spotify_mapping(conn, 41)
        old_market = get_market_price(conn, 31)
        new_market = get_market_price(conn, 41)
    finally:
        conn.close()

    assert counts["release_count_total"] == 1
    assert old_release is None
    assert new_release is not None
    assert new_mapping is not None
    assert new_mapping["spotify_album_id"] == "spotify:album:new"
    assert old_market is None
    assert new_market is not None
    assert new_market["currency"] == "EUR"
    assert get_setting("old_key") is None
    assert get_setting("new_key") == "new-value"


def test_import_collection_rejects_newer_schema(isolated_xdg, tmp_path):
    payload = {
        "schema_version": LATEST_SCHEMA_VERSION + 1,
        "release_count": 0,
        "settings": {},
        "releases": [],
    }
    input_path = tmp_path / "future.json"
    _write_payload(input_path, payload)

    with pytest.raises(ValueError, match="newer schema version"):
        run_import_collection(input_path=str(input_path))


def test_import_collection_rejects_release_count_mismatch(isolated_xdg, tmp_path):
    payload = {
        "schema_version": LATEST_SCHEMA_VERSION,
        "release_count": 2,
        "settings": {},
        "releases": [_release(1)],
    }
    input_path = tmp_path / "bad-count.json"
    _write_payload(input_path, payload)

    with pytest.raises(ValueError, match="release_count does not match"):
        run_import_collection(input_path=str(input_path))
