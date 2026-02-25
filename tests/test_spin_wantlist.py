
from __future__ import annotations

from discogs_player.data.db import get_connection
from discogs_player.data.repo import upsert_wantlist_entries
from discogs_player.use_cases.spin_wantlist import NoWantlistItemsFoundError, run_spin_wantlist

def _wantlist_entry(release_id: int, artist: str = "Artist", title: str = "Title", year: int = 2000, genres: list[str] | None = None):
    return {
        "discogs_release_id": release_id,
        "artist": artist,
        "title": title,
        "year": year,
        "is_active": 1,
        "genres": genres or [],
    }

def test_run_spin_wantlist(isolated_xdg):
    conn = get_connection()
    try:
        upsert_wantlist_entries(
            conn,
            [
                _wantlist_entry(101, artist="A", year=1999),
                _wantlist_entry(102, artist="B", year=2000),
                _wantlist_entry(103, artist="C", year=2001, genres=["Rock"]),
            ],
        )
    finally:
        conn.close()

    # Test basic spin
    result = run_spin_wantlist(seed=1)
    assert result["discogs_release_id"] == 101

    # Test with query
    result = run_spin_wantlist(q="A", seed=1)
    assert result["discogs_release_id"] == 101

    # Test with year
    result = run_spin_wantlist(year="2001", seed=1)
    assert result["discogs_release_id"] == 103

    # Test with genre
    result = run_spin_wantlist(genres=["Rock"], seed=1)
    assert result["discogs_release_id"] == 103

    # Test no results
    try:
        run_spin_wantlist(q="Nonexistent")
        assert False, "Should have raised NoWantlistItemsFoundError"
    except NoWantlistItemsFoundError:
        pass
