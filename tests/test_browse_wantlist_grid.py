from __future__ import annotations

from discogs_player.data.db import get_connection
from discogs_player.data.repo import (
    upsert_wantlist_entries,
    upsert_wantlist_market_price,
)
from discogs_player.use_cases import browse_wantlist_grid


def _wantlist_entry(
    release_id: int,
    *,
    artist: str = "Artist",
    title: str = "Title",
    year: int = 2020,
    genres: list[str] | None = None,
    styles: list[str] | None = None,
    cover_url: str = "https://example.test/cover.jpg",
) -> dict[str, object]:
    return {
        "discogs_release_id": release_id,
        "artist": artist,
        "title": title,
        "year": year,
        "genres": genres or ["Rock"],
        "styles": styles or ["Indie"],
        "thumb_url": "https://example.test/thumb.jpg",
        "cover_url": cover_url,
        "notes": "Must buy",
        "added_at": "2026-01-01T00:00:00Z",
        "last_synced_at": "2026-01-01T00:00:00Z",
        "is_active": 1,
    }


def test_run_browse_wantlist_grid_without_preload(isolated_xdg):
    conn = get_connection()
    try:
        upsert_wantlist_entries(conn, [_wantlist_entry(501)])
        conn.execute(
            """
            INSERT INTO spotify_mapping(discogs_release_id, spotify_album_id, confidence, last_checked_at, is_override)
            VALUES (?, ?, ?, ?, ?)
            """,
            (501, "spotify:album:501", 0.91, "2026-02-13T00:00:00Z", 0),
        )
        upsert_wantlist_market_price(
            conn,
            discogs_release_id=501,
            lowest=10.0,
            median=15.0,
            highest=20.0,
            currency="USD",
            last_updated_at="2026-02-08T00:00:00+00:00",
        )
    finally:
        conn.close()

    items = browse_wantlist_grid.run_browse_wantlist_grid(
        limit=10, preload_covers=False
    )
    assert len(items) == 1
    assert items[0]["discogs_release_id"] == 501
    assert items[0]["cover_path"] is None
    assert items[0]["spotify_album_id"] == "spotify:album:501"
    assert items[0]["market_median"] == 15.0
    assert items[0]["market_currency"] == "USD"


def test_run_browse_wantlist_grid_with_preload(monkeypatch, isolated_xdg):
    conn = get_connection()
    try:
        upsert_wantlist_entries(conn, [_wantlist_entry(601)])
    finally:
        conn.close()

    monkeypatch.setattr(
        browse_wantlist_grid,
        "get_or_fetch_cover_path",
        lambda cover_url: "/tmp/fake-wantlist-cover.img" if cover_url else None,
    )
    items = browse_wantlist_grid.run_browse_wantlist_grid(limit=10, preload_covers=True)

    assert len(items) == 1
    assert items[0]["discogs_release_id"] == 601
    assert items[0]["cover_path"] == "/tmp/fake-wantlist-cover.img"


def test_run_browse_wantlist_grid_applies_high_res_cover_preference(
    monkeypatch, isolated_xdg
):
    conn = get_connection()
    try:
        upsert_wantlist_entries(
            conn,
            [
                _wantlist_entry(
                    651,
                    cover_url=(
                        "https://i.discogs.com/xyz/rs:fit/h:600/w:600/format:webp/"
                        "discogs-images/R-651-1700000000-0000.jpg"
                    ),
                )
            ],
        )
    finally:
        conn.close()

    monkeypatch.setattr(
        browse_wantlist_grid, "get_high_res_art_preference", lambda: (True, 1300)
    )
    captured_urls: list[str] = []

    def _fake_fetch(cover_url: str | None) -> str | None:
        if not cover_url:
            return None
        captured_urls.append(cover_url)
        return "/tmp/high-res-wantlist-cover.img"

    monkeypatch.setattr(browse_wantlist_grid, "get_or_fetch_cover_path", _fake_fetch)

    items = browse_wantlist_grid.run_browse_wantlist_grid(limit=10, preload_covers=True)

    assert len(items) == 1
    assert "/h:1300/w:1300/" in str(items[0]["cover_url"])
    assert captured_urls == [items[0]["cover_url"]]
    assert items[0]["cover_path"] == "/tmp/high-res-wantlist-cover.img"


def test_run_browse_wantlist_grid_filters(isolated_xdg):
    conn = get_connection()
    try:
        upsert_wantlist_entries(
            conn,
            [
                _wantlist_entry(701, artist="A", title="Match", year=1999),
                _wantlist_entry(702, artist="B", title="Miss", year=2000),
            ],
        )
    finally:
        conn.close()

    items = browse_wantlist_grid.run_browse_wantlist_grid(
        limit=10,
        year="1990:1999",
        preload_covers=False,
    )
    assert len(items) == 1
    assert items[0]["discogs_release_id"] == 701
