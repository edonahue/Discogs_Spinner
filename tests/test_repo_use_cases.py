from __future__ import annotations

import sqlite3

import pytest

from discogs_player.core.settings import set_setting
from discogs_player.data.db import LATEST_SCHEMA_VERSION, get_connection
from discogs_player.data.repo import (
    get_release_counts,
    get_wantlist_count,
    insert_market_value_snapshot,
    query_market_value_snapshots,
    query_releases_missing_market_values,
    query_releases,
    query_wantlist,
    upsert_market_price,
    upsert_releases,
    upsert_wantlist_entries,
)
from discogs_player.use_cases.list_releases import parse_year_range
from discogs_player.use_cases.status_report import get_status_report


def _release(
    release_id: int,
    *,
    artist: str,
    title: str,
    year: int,
    genres: list[str],
    styles: list[str],
):
    return {
        "discogs_release_id": release_id,
        "artist": artist,
        "title": title,
        "year": year,
        "genres": genres,
        "styles": styles,
        "thumb_url": None,
        "cover_url": None,
        "added_at": "2026-01-01T00:00:00Z",
        "last_synced_at": "2026-01-01T00:00:00Z",
        "is_active": 1,
    }


def test_db_schema_is_created(isolated_xdg):
    conn = get_connection()
    try:
        names = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        user_version = int(conn.execute("PRAGMA user_version").fetchone()[0])
    finally:
        conn.close()

    assert {
        "releases",
        "spotify_mapping",
        "app_settings",
        "wantlist",
        "market_prices",
        "market_value_snapshots",
        "release_tracklist_cache",
        "release_tracks",
        "wantlist_market_prices",
        "wantlist_tracklist_cache",
        "wantlist_tracks",
    }.issubset(names)
    assert user_version == LATEST_SCHEMA_VERSION


def test_db_migrates_legacy_v0_database(isolated_xdg, tmp_path):
    legacy_path = tmp_path / "legacy.db"
    legacy_conn = sqlite3.connect(legacy_path)
    try:
        legacy_conn.executescript(
            """
            CREATE TABLE releases (
                discogs_release_id INTEGER PRIMARY KEY,
                artist TEXT,
                title TEXT,
                year INTEGER,
                genres TEXT,
                styles TEXT,
                thumb_url TEXT,
                cover_url TEXT,
                added_at TEXT,
                last_synced_at TEXT,
                is_active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE spotify_mapping (
                discogs_release_id INTEGER PRIMARY KEY,
                spotify_album_id TEXT,
                confidence REAL,
                last_checked_at TEXT,
                is_override INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE app_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            PRAGMA user_version = 0;
            """
        )
        legacy_conn.commit()
    finally:
        legacy_conn.close()

    conn = get_connection(path=legacy_path)
    try:
        names = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        index_names = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index'"
            ).fetchall()
        }
        user_version = int(conn.execute("PRAGMA user_version").fetchone()[0])
    finally:
        conn.close()

    assert {
        "releases",
        "spotify_mapping",
        "app_settings",
        "wantlist",
        "market_prices",
        "market_value_snapshots",
        "release_tracklist_cache",
        "release_tracks",
        "wantlist_market_prices",
        "wantlist_tracklist_cache",
        "wantlist_tracks",
    }.issubset(names)
    assert {
        "idx_releases_is_active",
        "idx_releases_year",
        "idx_releases_artist_title",
        "idx_wantlist_is_active",
        "idx_wantlist_year",
        "idx_wantlist_artist_title",
        "idx_market_prices_last_updated_at",
        "idx_market_prices_currency",
        "idx_market_value_snapshots_captured_at",
        "idx_release_tracklist_cache_last_refreshed_at",
        "idx_release_tracks_release_id_seq",
        "idx_wantlist_market_prices_last_updated_at",
        "idx_wantlist_market_prices_currency",
        "idx_wantlist_tracklist_cache_last_refreshed_at",
        "idx_wantlist_tracks_release_id_seq",
    }.issubset(index_names)
    assert user_version == LATEST_SCHEMA_VERSION


def test_db_migrates_v1_database_to_v4(isolated_xdg, tmp_path):
    legacy_path = tmp_path / "legacy-v1.db"
    legacy_conn = sqlite3.connect(legacy_path)
    try:
        legacy_conn.executescript(
            """
            CREATE TABLE releases (
                discogs_release_id INTEGER PRIMARY KEY,
                artist TEXT,
                title TEXT,
                year INTEGER,
                genres TEXT,
                styles TEXT,
                thumb_url TEXT,
                cover_url TEXT,
                added_at TEXT,
                last_synced_at TEXT,
                is_active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE spotify_mapping (
                discogs_release_id INTEGER PRIMARY KEY,
                spotify_album_id TEXT,
                confidence REAL,
                last_checked_at TEXT,
                is_override INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE app_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            CREATE INDEX idx_releases_is_active ON releases(is_active);
            CREATE INDEX idx_releases_year ON releases(year);
            CREATE INDEX idx_releases_artist_title ON releases(artist, title);
            PRAGMA user_version = 1;
            """
        )
        legacy_conn.commit()
    finally:
        legacy_conn.close()

    conn = get_connection(path=legacy_path)
    try:
        names = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        user_version = int(conn.execute("PRAGMA user_version").fetchone()[0])
    finally:
        conn.close()

    assert {
        "wantlist",
        "market_prices",
        "market_value_snapshots",
        "release_tracklist_cache",
        "release_tracks",
        "wantlist_market_prices",
        "wantlist_tracklist_cache",
        "wantlist_tracks",
    }.issubset(names)
    assert user_version == LATEST_SCHEMA_VERSION


def test_db_migrates_v3_database_to_v4(isolated_xdg, tmp_path):
    legacy_path = tmp_path / "legacy-v3.db"
    legacy_conn = sqlite3.connect(legacy_path)
    try:
        legacy_conn.executescript(
            """
            CREATE TABLE releases (
                discogs_release_id INTEGER PRIMARY KEY,
                artist TEXT,
                title TEXT,
                year INTEGER,
                genres TEXT,
                styles TEXT,
                thumb_url TEXT,
                cover_url TEXT,
                added_at TEXT,
                last_synced_at TEXT,
                is_active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE spotify_mapping (
                discogs_release_id INTEGER PRIMARY KEY,
                spotify_album_id TEXT,
                confidence REAL,
                last_checked_at TEXT,
                is_override INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE app_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            CREATE TABLE wantlist (
                discogs_release_id INTEGER PRIMARY KEY,
                artist TEXT,
                title TEXT,
                year INTEGER,
                genres TEXT,
                styles TEXT,
                thumb_url TEXT,
                cover_url TEXT,
                notes TEXT,
                added_at TEXT,
                last_synced_at TEXT,
                is_active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE market_prices (
                discogs_release_id INTEGER PRIMARY KEY,
                lowest REAL,
                median REAL,
                highest REAL,
                currency TEXT,
                last_updated_at TEXT
            );
            PRAGMA user_version = 3;
            """
        )
        legacy_conn.commit()
    finally:
        legacy_conn.close()

    conn = get_connection(path=legacy_path)
    try:
        names = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        user_version = int(conn.execute("PRAGMA user_version").fetchone()[0])
    finally:
        conn.close()

    assert {
        "market_value_snapshots",
        "release_tracklist_cache",
        "release_tracks",
        "wantlist_market_prices",
        "wantlist_tracklist_cache",
        "wantlist_tracks",
    }.issubset(names)
    assert user_version == LATEST_SCHEMA_VERSION


def test_repo_filters_and_counts(isolated_xdg):
    conn = get_connection()
    try:
        upsert_releases(
            conn,
            [
                _release(
                    1,
                    artist="Miles Davis",
                    title="Kind of Blue",
                    year=1959,
                    genres=["Jazz"],
                    styles=["Modal"],
                ),
                _release(
                    2,
                    artist="Nirvana",
                    title="Nevermind",
                    year=1991,
                    genres=["Rock"],
                    styles=["Grunge"],
                ),
                _release(
                    3,
                    artist="Alton Ellis",
                    title="Rocksteady",
                    year=1967,
                    genres=["Rocksteady"],
                    styles=["Ska"],
                ),
            ],
        )

        conn.execute(
            """
            INSERT INTO spotify_mapping(discogs_release_id, spotify_album_id, confidence, last_checked_at, is_override)
            VALUES (?, ?, ?, ?, ?)
            """,
            (1, "spotify:album:1", 0.9, "2026-01-01T00:00:00Z", 0),
        )
        conn.commit()

        rock_matches = query_releases(conn, genres=["Rock"], limit=20)
        assert [item["discogs_release_id"] for item in rock_matches] == [2]

        grunge_matches = query_releases(conn, styles=["Grunge"], limit=20)
        assert [item["discogs_release_id"] for item in grunge_matches] == [2]

        unmatched = query_releases(conn, unmatched=True, limit=20)
        assert [item["discogs_release_id"] for item in unmatched] == [3, 2]

        counts = get_release_counts(conn)
        assert counts == {
            "release_count_total": 3,
            "release_count_active": 3,
            "mapped_count": 1,
            "unmatched_count": 2,
        }

        upsert_market_price(
            conn,
            discogs_release_id=2,
            lowest=10.0,
            median=12.0,
            highest=14.0,
            currency="USD",
            last_updated_at="2026-02-07T00:00:00+00:00",
        )
        with_value = query_releases(conn, include_market=True, limit=20)
        by_id = {int(item["discogs_release_id"]): item for item in with_value}
        assert by_id[2]["market_median"] == 12.0
        assert by_id[1]["market_median"] is None
        assert by_id[3]["market_currency"] is None
    finally:
        conn.close()


def test_parse_year_range_validation():
    year_range = parse_year_range("1990:1999")
    assert year_range.start == 1990
    assert year_range.end == 1999

    exact = parse_year_range("2001")
    assert exact.start == 2001
    assert exact.end == 2001

    with pytest.raises(ValueError):
        parse_year_range("1999:1990")

    with pytest.raises(ValueError):
        parse_year_range("abc")

    with pytest.raises(ValueError):
        parse_year_range(":")


def test_status_report_shape_and_values(isolated_xdg):
    conn = get_connection()
    try:
        upsert_releases(
            conn,
            [
                _release(
                    7,
                    artist="Portishead",
                    title="Dummy",
                    year=1994,
                    genres=["Electronic"],
                    styles=["Trip Hop"],
                )
            ],
        )
        set_setting("last_sync_time", "2026-02-07T00:00:00+00:00", conn=conn)
        set_setting("last_spin_release_id", "7", conn=conn)
        set_setting("default_spotify_device_id", "device-1", conn=conn)
        set_setting("default_spotify_device_name", "Desk", conn=conn)
        upsert_wantlist_entries(
            conn,
            [
                {
                    "discogs_release_id": 991,
                    "artist": "The Clash",
                    "title": "London Calling",
                    "year": 1979,
                    "genres": ["Rock"],
                    "styles": ["Punk"],
                    "thumb_url": None,
                    "cover_url": None,
                    "notes": None,
                    "added_at": "2026-02-07T00:00:00+00:00",
                    "last_synced_at": "2026-02-07T00:00:00+00:00",
                    "is_active": 1,
                }
            ],
        )
    finally:
        conn.close()

    report = get_status_report()

    assert report["release_count_total"] == 1
    assert report["release_count_active"] == 1
    assert report["mapped_count"] == 0
    assert report["unmatched_count"] == 1
    assert report["wantlist_count_total"] == 1
    assert report["wantlist_count_active"] == 1
    assert report["wantlist_mapped_count"] == 0
    assert report["wantlist_unmatched_count"] == 1
    assert report["last_sync_time"] == "2026-02-07T00:00:00+00:00"
    assert report["last_spin_release_id"] == 7
    assert report["default_spotify_device"] == {"id": "device-1", "name": "Desk"}
    assert report["market_value_last_updated"] is None
    assert report["wantlist_count"] == 1
    assert isinstance(report["provider_readiness"], dict)
    assert report["provider_readiness"]["schema_version"] == 2
    # Backward-compatible Spotify-shaped payload remains available for legacy adapters.
    assert isinstance(report["spotify_capability"], dict)
    assert "addon_available" in report["spotify_capability"]
    assert "configured" in report["spotify_capability"]
    assert "action_label" in report["spotify_capability"]
    assert "status_message" in report["spotify_capability"]


def test_wantlist_repo_filters_and_count(isolated_xdg):
    conn = get_connection()
    try:
        upsert_wantlist_entries(
            conn,
            [
                {
                    "discogs_release_id": 101,
                    "artist": "Nirvana",
                    "title": "Bleach",
                    "year": 1989,
                    "genres": ["Rock"],
                    "styles": ["Grunge"],
                    "thumb_url": None,
                    "cover_url": None,
                    "notes": "first pressing",
                    "added_at": "2026-01-01T00:00:00Z",
                    "last_synced_at": "2026-01-02T00:00:00Z",
                    "is_active": 1,
                },
                {
                    "discogs_release_id": 102,
                    "artist": "Miles Davis",
                    "title": "Bitches Brew",
                    "year": 1970,
                    "genres": ["Jazz"],
                    "styles": ["Fusion"],
                    "thumb_url": None,
                    "cover_url": None,
                    "notes": None,
                    "added_at": "2026-01-03T00:00:00Z",
                    "last_synced_at": "2026-01-03T00:00:00Z",
                    "is_active": 1,
                },
                {
                    "discogs_release_id": 103,
                    "artist": "The Cure",
                    "title": "Disintegration",
                    "year": 1989,
                    "genres": ["Rock"],
                    "styles": ["Alternative Rock"],
                    "thumb_url": None,
                    "cover_url": None,
                    "notes": None,
                    "added_at": "2026-01-04T00:00:00Z",
                    "last_synced_at": "2026-01-04T00:00:00Z",
                    "is_active": 0,
                },
            ],
        )

        rock_items = query_wantlist(conn, genres=["Rock"], limit=20)
        assert [item["discogs_release_id"] for item in rock_items] == [101]

        by_year = query_wantlist(conn, year_from=1980, year_to=1990, limit=20)
        assert [item["discogs_release_id"] for item in by_year] == [101]

        upsert_releases(
            conn,
            [
                _release(
                    101,
                    artist="Nirvana",
                    title="Bleach",
                    year=1989,
                    genres=["Rock"],
                    styles=["Grunge"],
                )
            ],
        )
        upsert_market_price(
            conn,
            discogs_release_id=101,
            lowest=20.0,
            median=25.0,
            highest=30.0,
            currency="USD",
            last_updated_at="2026-02-07T00:00:00+00:00",
        )
        want_with_value = query_wantlist(conn, include_market=True, limit=20)
        by_id = {int(item["discogs_release_id"]): item for item in want_with_value}
        assert by_id[101]["market_lowest"] == 20.0
        assert by_id[102]["market_lowest"] is None

        assert get_wantlist_count(conn) == 2
    finally:
        conn.close()


def test_query_releases_missing_market_values(isolated_xdg):
    conn = get_connection()
    try:
        upsert_releases(
            conn,
            [
                _release(
                    11,
                    artist="Alpha",
                    title="No Price",
                    year=1990,
                    genres=["Rock"],
                    styles=["Alt"],
                ),
                _release(
                    22,
                    artist="Beta",
                    title="Has Price",
                    year=1991,
                    genres=["Rock"],
                    styles=["Alt"],
                ),
                _release(
                    33,
                    artist="Gamma",
                    title="Null Price Row",
                    year=1992,
                    genres=["Rock"],
                    styles=["Alt"],
                ),
                {
                    **_release(
                        44,
                        artist="Delta",
                        title="Inactive",
                        year=1993,
                        genres=["Rock"],
                        styles=["Alt"],
                    ),
                    "is_active": 0,
                },
            ],
        )
        upsert_market_price(
            conn,
            discogs_release_id=22,
            lowest=5.0,
            median=7.0,
            highest=9.0,
            currency="USD",
            last_updated_at="2026-02-07T00:00:00+00:00",
        )
        upsert_market_price(
            conn,
            discogs_release_id=33,
            lowest=None,
            median=None,
            highest=None,
            currency="USD",
            last_updated_at="2026-02-07T00:00:00+00:00",
        )

        rows = query_releases_missing_market_values(conn, limit=20)
        assert [item["discogs_release_id"] for item in rows] == [11, 33]
    finally:
        conn.close()


def test_market_value_snapshot_repo_roundtrip(isolated_xdg):
    conn = get_connection()
    try:
        id_one = insert_market_value_snapshot(
            conn,
            captured_at="2026-02-07T00:00:00+00:00",
            active_release_count=10,
            priced_release_count=8,
            unpriced_release_count=2,
            total_lowest=100.0,
            total_median=130.0,
            total_highest=170.0,
        )
        id_two = insert_market_value_snapshot(
            conn,
            captured_at="2026-02-08T00:00:00+00:00",
            active_release_count=11,
            priced_release_count=9,
            unpriced_release_count=2,
            total_lowest=110.0,
            total_median=140.0,
            total_highest=180.0,
        )

        points = query_market_value_snapshots(conn, limit=10)
    finally:
        conn.close()

    assert [item["id"] for item in points] == [id_two, id_one]
    assert points[0]["total_median"] == 140.0
    assert points[1]["captured_at"] == "2026-02-07T00:00:00+00:00"
