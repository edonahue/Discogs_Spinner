from __future__ import annotations

from discogs_player.data.db import get_connection
from discogs_player.data.repo import upsert_releases
from discogs_player.use_cases import browse_release_grid


def _release(release_id: int) -> dict[str, object]:
    return {
        "discogs_release_id": release_id,
        "artist": "Massive Attack",
        "title": "Mezzanine",
        "year": 1998,
        "genres": ["Electronic"],
        "styles": ["Trip Hop"],
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

