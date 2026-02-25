from __future__ import annotations

import csv
import json

from discogs_player.data.db import get_connection
from discogs_player.data.repo import get_spotify_mapping, upsert_releases, upsert_spotify_mapping
from discogs_player.use_cases.bootstrap_import import run_bootstrap_mapping_import


def _release(release_id: int) -> dict[str, object]:
    return {
        "discogs_release_id": release_id,
        "artist": f"Artist {release_id}",
        "title": f"Album {release_id}",
        "year": 2000 + (release_id % 20),
        "genres": ["Rock"],
        "styles": ["Indie"],
        "thumb_url": None,
        "cover_url": None,
        "added_at": "2026-02-01T00:00:00Z",
        "last_synced_at": "2026-02-01T00:00:00Z",
        "is_active": 1,
    }


def test_bootstrap_import_direct_csv_merge_behaviour(isolated_xdg, tmp_path):
    conn = get_connection()
    try:
        upsert_releases(conn, [_release(1), _release(2), _release(3)])
        upsert_spotify_mapping(
            conn,
            discogs_release_id=2,
            spotify_album_id="EXISTING2",
            confidence=0.91,
            last_checked_at="2026-02-01T00:00:00Z",
            is_override=False,
        )
        upsert_spotify_mapping(
            conn,
            discogs_release_id=3,
            spotify_album_id="LOCKED3",
            confidence=1.0,
            last_checked_at="2026-02-01T00:00:00Z",
            is_override=True,
        )
    finally:
        conn.close()

    csv_path = tmp_path / "bootstrap.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["discogs_release_id", "spotify_album_id"],
        )
        writer.writeheader()
        writer.writerow({"discogs_release_id": "1", "spotify_album_id": "spotify:album:NEW1"})
        writer.writerow({"discogs_release_id": "2", "spotify_album_id": "spotify:album:NEW2"})
        writer.writerow({"discogs_release_id": "3", "spotify_album_id": "spotify:album:NEW3"})
        writer.writerow({"discogs_release_id": "4", "spotify_album_id": "spotify:album:MISS4"})
        writer.writerow(
            {"discogs_release_id": "5", "spotify_album_id": "spotify:track:unsupported"}
        )

    result = run_bootstrap_mapping_import(
        input_path=str(csv_path),
        source_format="direct",
        conflict_mode="merge",
        dry_run=False,
    )

    assert result["source_format_used"] == "direct"
    assert result["parsed_mapping_count"] == 4
    assert result["invalid_row_count"] == 1
    assert result["imported_mapping_count"] == 1
    assert result["skipped_existing_mapping_count"] == 1
    assert result["skipped_override_mapping_count"] == 1
    assert result["skipped_missing_release_count"] == 1

    conn = get_connection()
    try:
        mapping_1 = get_spotify_mapping(conn, 1)
        mapping_2 = get_spotify_mapping(conn, 2)
        mapping_3 = get_spotify_mapping(conn, 3)
        mapping_4 = get_spotify_mapping(conn, 4)
    finally:
        conn.close()

    assert mapping_1 is not None
    assert mapping_1["spotify_album_id"] == "NEW1"
    assert mapping_2 is not None
    assert mapping_2["spotify_album_id"] == "EXISTING2"
    assert mapping_3 is not None
    assert mapping_3["spotify_album_id"] == "LOCKED3"
    assert mapping_4 is None


def test_bootstrap_import_discofy_nested_json(isolated_xdg, tmp_path):
    conn = get_connection()
    try:
        upsert_releases(conn, [_release(11), _release(12)])
    finally:
        conn.close()

    payload = {
        "status": "complete",
        "transfer_collection_status": {
            "results": [
                {
                    "discogs": {"release_id": 11},
                    "spotify": {
                        "spotify_album_uri": "spotify:album:DISC11",
                        "confidence": 0.92,
                    },
                },
                {
                    "discogs_id": "12",
                    "spotify_uri": "https://open.spotify.com/album/DISC12?si=abc",
                },
            ]
        },
    }
    input_path = tmp_path / "discofy.json"
    input_path.write_text(json.dumps(payload), encoding="utf-8")

    result = run_bootstrap_mapping_import(
        input_path=str(input_path),
        source_format="discofy",
        conflict_mode="merge",
        default_confidence=0.88,
    )

    assert result["source_format_used"] == "discofy"
    assert result["parsed_mapping_count"] == 2
    assert result["imported_mapping_count"] == 2
    assert result["invalid_row_count"] == 0

    conn = get_connection()
    try:
        mapping_11 = get_spotify_mapping(conn, 11)
        mapping_12 = get_spotify_mapping(conn, 12)
    finally:
        conn.close()

    assert mapping_11 is not None
    assert mapping_11["spotify_album_id"] == "DISC11"
    assert mapping_11["confidence"] == 0.92
    assert mapping_12 is not None
    assert mapping_12["spotify_album_id"] == "DISC12"
    assert mapping_12["confidence"] == 0.88


def test_bootstrap_import_auto_uses_direct_for_csv(isolated_xdg, tmp_path):
    conn = get_connection()
    try:
        upsert_releases(conn, [_release(21)])
    finally:
        conn.close()

    csv_path = tmp_path / "auto.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["discogs_release_id", "spotify_album_id", "confidence"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "discogs_release_id": "21",
                "spotify_album_id": "https://open.spotify.com/album/AUTO21",
                "confidence": "0.77",
            }
        )

    result = run_bootstrap_mapping_import(
        input_path=str(csv_path),
        source_format="auto",
        dry_run=True,
    )

    assert result["input_kind"] == "csv"
    assert result["source_format_used"] == "direct"
    assert result["parsed_mapping_count"] == 1
    assert result["imported_mapping_count"] == 1


def test_bootstrap_import_accepts_discogs_to_spotify_alias(isolated_xdg, tmp_path):
    conn = get_connection()
    try:
        upsert_releases(conn, [_release(41)])
    finally:
        conn.close()

    payload = {
        "transfer_collection_status": {
            "results": [
                {
                    "discogs": {"release_id": 41},
                    "spotify": {"spotify_album_uri": "spotify:album:ALIAS41"},
                }
            ]
        }
    }
    input_path = tmp_path / "discogs_to_spotify.json"
    input_path.write_text(json.dumps(payload), encoding="utf-8")

    result = run_bootstrap_mapping_import(
        input_path=str(input_path),
        source_format="discogs-to-spotify",
        conflict_mode="merge",
    )

    assert result["source_format_requested"] == "discofy"
    assert result["source_format_used"] == "discofy"
    assert result["parsed_mapping_count"] == 1
    assert result["imported_mapping_count"] == 1

    conn = get_connection()
    try:
        mapping = get_spotify_mapping(conn, 41)
    finally:
        conn.close()

    assert mapping is not None
    assert mapping["spotify_album_id"] == "ALIAS41"


def test_bootstrap_import_replace_clears_existing_mappings(isolated_xdg, tmp_path):
    conn = get_connection()
    try:
        upsert_releases(conn, [_release(31), _release(32)])
        upsert_spotify_mapping(
            conn,
            discogs_release_id=31,
            spotify_album_id="OLD31",
            confidence=0.51,
            last_checked_at="2026-02-01T00:00:00Z",
            is_override=False,
        )
    finally:
        conn.close()

    payload = {"mappings": [{"discogs_release_id": 32, "spotify_album_id": "spotify:album:NEW32"}]}
    input_path = tmp_path / "replace.json"
    input_path.write_text(json.dumps(payload), encoding="utf-8")

    result = run_bootstrap_mapping_import(
        input_path=str(input_path),
        source_format="direct",
        conflict_mode="replace",
    )

    assert result["imported_mapping_count"] == 1

    conn = get_connection()
    try:
        old_mapping = get_spotify_mapping(conn, 31)
        new_mapping = get_spotify_mapping(conn, 32)
    finally:
        conn.close()

    assert old_mapping is None
    assert new_mapping is not None
    assert new_mapping["spotify_album_id"] == "NEW32"
