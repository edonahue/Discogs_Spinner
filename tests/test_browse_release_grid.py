from __future__ import annotations

from discogs_player.data.db import get_connection
from discogs_player.data.repo import upsert_market_price, upsert_releases
from discogs_player.use_cases import browse_release_grid


def _release(
    release_id: int,
    *,
    artist: str = "Massive Attack",
    title: str = "Mezzanine",
    year: int = 1998,
    genres: list[str] | None = None,
    styles: list[str] | None = None,
    cover_url: str = "https://example.test/cover.jpg",
) -> dict[str, object]:
    return {
        "discogs_release_id": release_id,
        "artist": artist,
        "title": title,
        "year": year,
        "genres": genres or ["Electronic"],
        "styles": styles or ["Trip Hop"],
        "thumb_url": "https://example.test/thumb.jpg",
        "cover_url": cover_url,
        "added_at": "2026-01-01T00:00:00Z",
        "last_synced_at": "2026-01-01T00:00:00Z",
        "is_active": 1,
    }


def test_run_browse_release_grid_without_preload(isolated_xdg):
    conn = get_connection()
    try:
        upsert_releases(conn, [_release(101)])
        upsert_market_price(
            conn,
            discogs_release_id=101,
            lowest=10.0,
            median=12.5,
            highest=17.0,
            currency="USD",
            last_updated_at="2026-02-08T00:00:00+00:00",
        )
    finally:
        conn.close()

    items = browse_release_grid.run_browse_release_grid(limit=10, preload_covers=False)
    assert len(items) == 1
    assert items[0]["discogs_release_id"] == 101
    assert items[0]["cover_path"] is None
    assert items[0]["genres"] == ["Electronic"]
    assert items[0]["styles"] == ["Trip Hop"]
    assert items[0]["thumb_url"] == "https://example.test/thumb.jpg"
    assert items[0]["added_at"] == "2026-01-01T00:00:00Z"
    assert items[0]["last_synced_at"] == "2026-01-01T00:00:00Z"
    assert items[0]["is_active"] is True
    assert items[0]["market_median"] == 12.5
    assert items[0]["market_currency"] == "USD"


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


def test_run_browse_release_grid_parallel_preload_deduplicates_cover_urls(
    monkeypatch, isolated_xdg
):
    conn = get_connection()
    try:
        upsert_releases(
            conn,
            [
                _release(301, title="A"),
                _release(302, title="B"),
                _release(303, title="C"),
            ],
        )
    finally:
        conn.close()

    calls = {"count": 0}

    def _fake_fetch(cover_url: str | None) -> str | None:
        if not cover_url:
            return None
        calls["count"] += 1
        return "/tmp/shared-cover.img"

    monkeypatch.setattr(browse_release_grid, "get_or_fetch_cover_path", _fake_fetch)

    items = browse_release_grid.run_browse_release_grid(limit=10, preload_covers=True)

    assert len(items) == 3
    assert all(item["cover_path"] == "/tmp/shared-cover.img" for item in items)
    assert calls["count"] == 1


def test_run_browse_release_grid_applies_high_res_cover_preference(
    monkeypatch, isolated_xdg
):
    conn = get_connection()
    try:
        upsert_releases(
            conn,
            [
                _release(
                    401,
                    cover_url=(
                        "https://i.discogs.com/abc/rs:fit/h:600/w:600/format:webp/"
                        "discogs-images/R-401-1700000000-0000.jpg"
                    ),
                )
            ],
        )
    finally:
        conn.close()

    monkeypatch.setattr(
        browse_release_grid, "get_high_res_art_preference", lambda: (True, 1400)
    )
    captured_urls: list[str] = []

    def _fake_fetch(cover_url: str | None) -> str | None:
        if not cover_url:
            return None
        captured_urls.append(cover_url)
        return "/tmp/high-res-release-cover.img"

    monkeypatch.setattr(browse_release_grid, "get_or_fetch_cover_path", _fake_fetch)

    items = browse_release_grid.run_browse_release_grid(limit=10, preload_covers=True)

    assert len(items) == 1
    assert "/h:1400/w:1400/" in str(items[0]["cover_url"])
    assert captured_urls == [items[0]["cover_url"]]
    assert items[0]["cover_path"] == "/tmp/high-res-release-cover.img"


def test_run_browse_release_grid_default_limit_includes_full_catalogue(isolated_xdg):
    conn = get_connection()
    try:
        upsert_releases(
            conn,
            [
                _release(
                    release_id,
                    artist=f"Artist {release_id}",
                    title=f"Album {release_id}",
                )
                for release_id in range(1, 76)
            ],
        )
    finally:
        conn.close()

    items = browse_release_grid.run_browse_release_grid(preload_covers=False)

    assert len(items) == 75
    assert {int(item["discogs_release_id"]) for item in items} == set(range(1, 76))


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
