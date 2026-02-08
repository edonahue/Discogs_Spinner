from __future__ import annotations

from discogs_player.data.db import get_connection
from discogs_player.data.repo import upsert_releases
from discogs_player.use_cases import browse_release_grid


def _release(
    release_id: int,
    *,
    artist: str = "Massive Attack",
    title: str = "Mezzanine",
    year: int = 1998,
    genres: list[str] | None = None,
    styles: list[str] | None = None,
) -> dict[str, object]:
    return {
        "discogs_release_id": release_id,
        "artist": artist,
        "title": title,
        "year": year,
        "genres": genres or ["Electronic"],
        "styles": styles or ["Trip Hop"],
        "thumb_url": "https://example.test/thumb.jpg",
        "cover_url": "https://example.test/cover.jpg",
        "added_at": "2026-01-01T00:00:00Z",
        "last_synced_at": "2026-01-01T00:00:00Z",
        "is_active": 1,
    }


def test_run_browse_release_grid_without_preload(isolated_xdg):
    conn = get_connection()
    try:
        upsert_releases(conn, [_release(101)])
    finally:
        conn.close()

    items = browse_release_grid.run_browse_release_grid(limit=10, preload_covers=False)
    assert len(items) == 1
    assert items[0]["discogs_release_id"] == 101
    assert items[0]["cover_path"] is None
    assert items[0]["genres"] == ["Electronic"]
    assert items[0]["styles"] == ["Trip Hop"]


def test_run_browse_release_grid_with_preload(monkeypatch, isolated_xdg):
    conn = get_connection()
    try:
        upsert_releases(conn, [_release(202)])
    finally:
        conn.close()

    monkeypatch.setattr(
        browse_release_grid,
        "get_or_fetch_cover_path",
        lambda cover_url: "/tmp/fake-cover.img" if cover_url else None,
    )
    items = browse_release_grid.run_browse_release_grid(limit=10, preload_covers=True)

    assert len(items) == 1
    assert items[0]["discogs_release_id"] == 202
    assert items[0]["cover_path"] == "/tmp/fake-cover.img"


def test_run_browse_release_grid_filters_by_year_and_tags(isolated_xdg):
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
                ),
                _release(
                    2,
                    artist="Miles Davis",
                    title="Kind of Blue",
                    year=1959,
                    genres=["Jazz"],
                    styles=["Modal"],
                ),
            ],
        )
    finally:
        conn.close()

    items = browse_release_grid.run_browse_release_grid(
        limit=10,
        year="1990:1999",
        genres=["Rock"],
        styles=["Grunge"],
        preload_covers=False,
    )
    assert [item["discogs_release_id"] for item in items] == [1]


def test_run_browse_release_grid_filters_unmatched(isolated_xdg):
    conn = get_connection()
    try:
        upsert_releases(
            conn,
            [
                _release(10, artist="A", title="Mapped"),
                _release(20, artist="B", title="Unmatched"),
            ],
        )
        conn.execute(
            """
            INSERT INTO spotify_mapping(discogs_release_id, spotify_album_id, confidence, last_checked_at, is_override)
            VALUES (?, ?, ?, ?, ?)
            """,
            (10, "spotify:album:10", 0.9, "2026-01-01T00:00:00Z", 0),
        )
        conn.commit()
    finally:
        conn.close()

    items = browse_release_grid.run_browse_release_grid(
        limit=10,
        unmatched=True,
        preload_covers=False,
    )
    assert [item["discogs_release_id"] for item in items] == [20]
