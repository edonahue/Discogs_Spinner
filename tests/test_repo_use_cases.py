from __future__ import annotations

import pytest

from discogs_player.core.settings import set_setting
from discogs_player.data.db import get_connection
from discogs_player.data.repo import get_release_counts, query_releases, upsert_releases
from discogs_player.use_cases.list_releases import parse_year_range
from discogs_player.use_cases.status_report import get_status_report


def _release(release_id: int, *, artist: str, title: str, year: int, genres: list[str], styles: list[str]):
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
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        }
    finally:
        conn.close()

    assert {"releases", "spotify_mapping", "app_settings"}.issubset(names)


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
    finally:
        conn.close()

    report = get_status_report()

    assert report["release_count_total"] == 1
    assert report["release_count_active"] == 1
    assert report["mapped_count"] == 0
    assert report["unmatched_count"] == 1
    assert report["last_sync_time"] == "2026-02-07T00:00:00+00:00"
    assert report["last_spin_release_id"] == 7
    assert report["default_spotify_device"] == {"id": "device-1", "name": "Desk"}
    assert report["market_value_last_updated"] is None
    assert report["wantlist_count"] is None
