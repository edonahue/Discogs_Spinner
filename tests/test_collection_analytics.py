from __future__ import annotations

from discogs_player.data.db import get_connection
from discogs_player.data.repo import upsert_releases
from discogs_player.use_cases.collection_analytics import run_collection_analytics


def _release(
    release_id: int,
    *,
    artist: str,
    title: str,
    year: int | None,
    genres: list[str],
    styles: list[str],
    added_at: str | None,
) -> dict[str, object]:
    return {
        "discogs_release_id": release_id,
        "artist": artist,
        "title": title,
        "year": year,
        "genres": genres,
        "styles": styles,
        "thumb_url": None,
        "cover_url": None,
        "added_at": added_at,
        "last_synced_at": "2026-01-01T00:00:00Z",
        "is_active": 1,
    }


def test_collection_analytics_summary_and_breakdowns(isolated_xdg):
    conn = get_connection()
    try:
        upsert_releases(
            conn,
            [
                _release(
                    1,
                    artist="Nirvana",
                    title="Nevermind",
                    year=1991,
                    genres=["Rock"],
                    styles=["Grunge"],
                    added_at="2026-01-10T00:00:00Z",
                ),
                _release(
                    2,
                    artist="Nirvana",
                    title="In Utero",
                    year=1993,
                    genres=["Rock", "Alternative"],
                    styles=["Grunge"],
                    added_at="2025-12-01T00:00:00Z",
                ),
                _release(
                    3,
                    artist="Miles Davis",
                    title="Kind of Blue",
                    year=1959,
                    genres=["Jazz"],
                    styles=["Modal"],
                    added_at="2026-02-01T00:00:00Z",
                ),
                _release(
                    4,
                    artist="Unknown Artist",
                    title="Unknown Album",
                    year=None,
                    genres=[],
                    styles=[],
                    added_at="not-a-date",
                ),
            ],
        )
        conn.execute(
            """
            INSERT INTO spotify_mapping(discogs_release_id, spotify_album_id, confidence, last_checked_at, is_override)
            VALUES (?, ?, ?, ?, ?)
            """,
            (1, "spotify:album:1", 0.91, "2026-02-07T00:00:00Z", 0),
        )
        conn.execute(
            """
            INSERT INTO spotify_mapping(discogs_release_id, spotify_album_id, confidence, last_checked_at, is_override)
            VALUES (?, ?, ?, ?, ?)
            """,
            (3, "spotify:album:3", 0.88, "2026-02-07T00:00:00Z", 0),
        )
        conn.commit()
    finally:
        conn.close()

    report = run_collection_analytics(limit=2)

    assert report["release_count_active"] == 4
    assert report["mapped_count"] == 2
    assert report["unmatched_count"] == 2
    assert report["top_limit"] == 2

    assert report["by_release_year"] == [
        {"year": 1959, "count": 1},
        {"year": 1991, "count": 1},
        {"year": 1993, "count": 1},
    ]
    assert report["acquisition_timeline"] == [
        {"year": 2025, "count": 1},
        {"year": 2026, "count": 2},
    ]
    assert report["top_genres"] == [
        {"genre": "Rock", "count": 2},
        {"genre": "Alternative", "count": 1},
    ]
    assert report["top_styles"] == [
        {"style": "Grunge", "count": 2},
        {"style": "Modal", "count": 1},
    ]
    assert report["top_artists"] == [
        {"artist": "Nirvana", "count": 2},
        {"artist": "Miles Davis", "count": 1},
    ]


def test_collection_analytics_rejects_invalid_limit():
    try:
        run_collection_analytics(limit=0)
    except ValueError as exc:
        assert "limit must be >= 1" in str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid limit")
