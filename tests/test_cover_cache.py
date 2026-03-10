"""Tests for the cover cache management use-cases."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import patch

import pytest

from discogs_player.use_cases.cover_cache import (
    run_cover_cache_prune,
    run_cover_cache_stats,
    run_cover_cache_warm,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_cache_file(cache_dir: Path, name: str, *, content: bytes = b"X" * 100) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    p = cache_dir / name
    p.write_bytes(content)
    return p


# ---------------------------------------------------------------------------
# run_cover_cache_stats
# ---------------------------------------------------------------------------

def test_cache_stats_empty(isolated_xdg):
    result = run_cover_cache_stats()
    assert result["item_count"] == 0
    assert result["total_bytes"] == 0
    assert result["oldest_entry_mtime"] is None
    assert result["newest_entry_mtime"] is None
    assert "cache_dir" in result


def test_cache_stats_with_files(isolated_xdg):
    from discogs_player.core.paths import cover_cache_dir

    cache_dir = cover_cache_dir()
    _make_cache_file(cache_dir, "aaa.jpg", content=b"A" * 200)
    _make_cache_file(cache_dir, "bbb.png", content=b"B" * 300)

    result = run_cover_cache_stats()

    assert result["item_count"] == 2
    assert result["total_bytes"] == 500
    assert result["oldest_entry_mtime"] is not None
    assert result["newest_entry_mtime"] is not None


def test_cache_stats_ignores_non_image_files(isolated_xdg):
    from discogs_player.core.paths import cover_cache_dir

    cache_dir = cover_cache_dir()
    _make_cache_file(cache_dir, "image.jpg")
    _make_cache_file(cache_dir, "readme.txt")  # should be ignored

    result = run_cover_cache_stats()
    assert result["item_count"] == 1


# ---------------------------------------------------------------------------
# run_cover_cache_prune
# ---------------------------------------------------------------------------

def test_cache_prune_rejects_invalid_days(isolated_xdg):
    with pytest.raises(ValueError, match="days must be >= 1"):
        run_cover_cache_prune(days=0)


def test_cache_prune_empty_dir(isolated_xdg):
    result = run_cover_cache_prune(days=30)
    assert result["deleted_count"] == 0
    assert result["freed_bytes"] == 0
    assert result["error_count"] == 0


def test_cache_prune_deletes_old_files(isolated_xdg):
    from discogs_player.core.paths import cover_cache_dir

    cache_dir = cover_cache_dir()
    old_file = _make_cache_file(cache_dir, "old.jpg", content=b"X" * 100)
    new_file = _make_cache_file(cache_dir, "new.jpg", content=b"Y" * 50)

    # Back-date the old file to 60 days ago
    old_ts = time.time() - 60 * 86400
    import os
    os.utime(str(old_file), (old_ts, old_ts))

    result = run_cover_cache_prune(days=30)

    assert result["deleted_count"] == 1
    assert result["freed_bytes"] == 100
    assert not old_file.exists()
    assert new_file.exists()


def test_cache_prune_keeps_recent_files(isolated_xdg):
    from discogs_player.core.paths import cover_cache_dir

    cache_dir = cover_cache_dir()
    recent = _make_cache_file(cache_dir, "recent.jpg")

    result = run_cover_cache_prune(days=30)

    assert result["deleted_count"] == 0
    assert recent.exists()


# ---------------------------------------------------------------------------
# run_cover_cache_warm
# ---------------------------------------------------------------------------

def test_cache_warm_rejects_invalid_limit(isolated_xdg):
    with pytest.raises(ValueError, match="limit must be >= 1"):
        run_cover_cache_warm(limit=0)


def test_cache_warm_empty_collection(isolated_xdg):
    result = run_cover_cache_warm()
    assert result["already_cached"] == 0
    assert result["no_url"] == 0
    assert result["fetched"] == 0
    assert result["fetch_errors"] == 0


def test_cache_warm_with_releases_no_url(isolated_xdg):
    from discogs_player.data.db import get_connection
    from discogs_player.data.repo import upsert_releases

    conn = get_connection()
    try:
        upsert_releases(conn, [
            {
                "discogs_release_id": 1,
                "artist": "Artist",
                "title": "Album",
                "year": 2000,
                "genres": [],
                "styles": [],
                "thumb_url": None,
                "cover_url": None,
                "added_at": "2026-01-01T00:00:00Z",
                "last_synced_at": "2026-01-01T00:00:00Z",
                "is_active": 1,
            }
        ])
    finally:
        conn.close()

    result = run_cover_cache_warm()
    assert result["no_url"] == 1
    assert result["fetched"] == 0


def test_cache_warm_already_cached(isolated_xdg):
    """Releases with a cached digest are counted as already_cached, not fetched."""
    import hashlib

    from discogs_player.core.paths import cover_cache_dir
    from discogs_player.data.db import get_connection
    from discogs_player.data.repo import upsert_releases

    cover_url = "https://i.discogs.com/cover.jpg"
    digest = hashlib.sha256(cover_url.encode("utf-8")).hexdigest()
    cache_dir = cover_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / f"{digest}.jpg").write_bytes(b"FAKEIMAGE")

    conn = get_connection()
    try:
        upsert_releases(conn, [
            {
                "discogs_release_id": 99,
                "artist": "Band",
                "title": "Record",
                "year": 2010,
                "genres": [],
                "styles": [],
                "thumb_url": None,
                "cover_url": cover_url,
                "added_at": "2026-01-01T00:00:00Z",
                "last_synced_at": "2026-01-01T00:00:00Z",
                "is_active": 1,
            }
        ])
    finally:
        conn.close()

    result = run_cover_cache_warm()
    assert result["already_cached"] == 1
    assert result["fetched"] == 0


def test_cache_warm_respects_limit(isolated_xdg):
    """When limit=0 is rejected; limit=1 fetches at most 1 missing cover."""
    from discogs_player.data.db import get_connection
    from discogs_player.data.repo import upsert_releases

    def _rel(rid: int, url: str) -> dict:
        return {
            "discogs_release_id": rid,
            "artist": "X",
            "title": f"T{rid}",
            "year": 2000,
            "genres": [],
            "styles": [],
            "thumb_url": None,
            "cover_url": url,
            "added_at": "2026-01-01T00:00:00Z",
            "last_synced_at": "2026-01-01T00:00:00Z",
            "is_active": 1,
        }

    conn = get_connection()
    try:
        upsert_releases(conn, [
            _rel(1, "https://i.discogs.com/a.jpg"),
            _rel(2, "https://i.discogs.com/b.jpg"),
        ])
    finally:
        conn.close()

    # Patch get_or_fetch_cover_path to avoid real HTTP
    with patch(
        "discogs_player.use_cases.cover_cache.get_or_fetch_cover_path",
        return_value=None,
    ) as mock_fetch:
        result = run_cover_cache_warm(limit=1)

    assert mock_fetch.call_count == 1
    assert result["fetch_errors"] == 1
    assert result["limit"] == 1
