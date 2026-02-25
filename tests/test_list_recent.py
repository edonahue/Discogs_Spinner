"""Tests for list_recent use case."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


from discogs_player.data.db import get_connection
from discogs_player.data.repo import upsert_releases
from discogs_player.use_cases.list_recent import run_recent_releases


def test_recent_releases_empty(isolated_xdg):
    """Test when no releases exist."""
    result = run_recent_releases(days=7, limit=10)
    
    assert result["ok"] is True
    assert result["releases"] == []
    assert result["count"] == 0
    assert result["days"] == 7
    assert result["limit"] == 10


def test_recent_releases_basic(isolated_xdg):
    """Test basic recent releases retrieval."""
    conn = get_connection()
    try:
        # Add releases with different dates
        now = datetime.now(timezone.utc)
        
        upsert_releases(conn, [
            {
                "discogs_release_id": 101,
                "artist": "Recent Artist",
                "title": "Recent Album",
                "year": 2024,
                "is_active": 1,
                "added_at": now.isoformat(),
            },
            {
                "discogs_release_id": 102,
                "artist": "Old Artist",
                "title": "Old Album",
                "year": 2020,
                "is_active": 1,
                "added_at": (now - timedelta(days=30)).isoformat(),
            },
        ])
    finally:
        conn.close()
    
    # Get releases from last 7 days
    result = run_recent_releases(days=7, limit=10)
    
    assert result["ok"] is True
    assert result["count"] == 1
    assert len(result["releases"]) == 1
    assert result["releases"][0]["discogs_release_id"] == 101
    assert result["releases"][0]["artist"] == "Recent Artist"


def test_recent_releases_with_limit(isolated_xdg):
    """Test limit parameter."""
    conn = get_connection()
    try:
        now = datetime.now(timezone.utc)
        
        # Add 5 recent releases
        upsert_releases(conn, [
            {
                "discogs_release_id": i,
                "artist": f"Artist {i}",
                "title": f"Album {i}",
                "year": 2024,
                "is_active": 1,
                "added_at": now.isoformat(),
            }
            for i in range(1, 6)
        ])
    finally:
        conn.close()
    
    # Get only 3
    result = run_recent_releases(days=7, limit=3)
    
    assert result["count"] == 3
    assert len(result["releases"]) == 3


def test_recent_releases_sorted_by_date(isolated_xdg):
    """Test that releases are sorted by added_at descending."""
    conn = get_connection()
    try:
        now = datetime.now(timezone.utc)
        
        upsert_releases(conn, [
            {
                "discogs_release_id": 1,
                "artist": "First",
                "title": "Album",
                "year": 2024,
                "is_active": 1,
                "added_at": (now - timedelta(days=2)).isoformat(),
            },
            {
                "discogs_release_id": 2,
                "artist": "Second",
                "title": "Album",
                "year": 2024,
                "is_active": 1,
                "added_at": now.isoformat(),
            },
            {
                "discogs_release_id": 3,
                "artist": "Third",
                "title": "Album",
                "year": 2024,
                "is_active": 1,
                "added_at": (now - timedelta(days=1)).isoformat(),
            },
        ])
    finally:
        conn.close()
    
    result = run_recent_releases(days=7, limit=10)
    
    # Should be sorted: 2 (most recent), 3, 1 (oldest)
    ids = [r["discogs_release_id"] for r in result["releases"]]
    assert ids == [2, 3, 1]


def test_recent_releases_excludes_inactive(isolated_xdg):
    """Test that inactive (soft-deleted) releases are excluded."""
    conn = get_connection()
    try:
        now = datetime.now(timezone.utc)
        
        upsert_releases(conn, [
            {
                "discogs_release_id": 101,
                "artist": "Active",
                "title": "Album",
                "year": 2024,
                "is_active": 1,
                "added_at": now.isoformat(),
            },
            {
                "discogs_release_id": 102,
                "artist": "Inactive",
                "title": "Album",
                "year": 2024,
                "is_active": 0,
                "added_at": now.isoformat(),
            },
        ])
    finally:
        conn.close()
    
    result = run_recent_releases(days=7, limit=10)
    
    assert result["count"] == 1
    assert result["releases"][0]["artist"] == "Active"


def test_recent_releases_with_market_data(isolated_xdg):
    """Test that market data is included when available."""
    conn = get_connection()
    try:
        now = datetime.now(timezone.utc)
        
        upsert_releases(conn, [
            {
                "discogs_release_id": 101,
                "artist": "Test",
                "title": "Album",
                "year": 2024,
                "is_active": 1,
                "added_at": now.isoformat(),
            },
        ])
        
        # Add market prices
        conn.execute(
            """
            INSERT INTO market_prices (discogs_release_id, lowest, median, highest, currency)
            VALUES (?, 10.0, 15.0, 20.0, 'USD')
            """,
            (101,)
        )
        conn.commit()
    finally:
        conn.close()
    
    result = run_recent_releases(days=7, limit=10, include_market=True)
    
    assert result["count"] == 1
    release = result["releases"][0]
    assert release["market_lowest"] == 10.0
    assert release["market_median"] == 15.0
    assert release["market_highest"] == 20.0
    assert release["market_currency"] == "USD"


def test_recent_releases_without_market_data(isolated_xdg):
    """Test without market data."""
    conn = get_connection()
    try:
        now = datetime.now(timezone.utc)
        
        upsert_releases(conn, [
            {
                "discogs_release_id": 101,
                "artist": "Test",
                "title": "Album",
                "year": 2024,
                "is_active": 1,
                "added_at": now.isoformat(),
            },
        ])
    finally:
        conn.close()
    
    result = run_recent_releases(days=7, limit=10, include_market=False)
    
    assert result["count"] == 1
    release = result["releases"][0]
    assert "market_lowest" not in release
    assert "market_median" not in release


def test_recent_releases_different_days_windows(isolated_xdg):
    """Test different days parameters."""
    conn = get_connection()
    try:
        now = datetime.now(timezone.utc)
        
        upsert_releases(conn, [
            {
                "discogs_release_id": 1,
                "artist": "Today",
                "title": "Album",
                "year": 2024,
                "is_active": 1,
                "added_at": now.isoformat(),
            },
            {
                "discogs_release_id": 2,
                "artist": "5 days ago",
                "title": "Album",
                "year": 2024,
                "is_active": 1,
                "added_at": (now - timedelta(days=5)).isoformat(),
            },
            {
                "discogs_release_id": 3,
                "artist": "15 days ago",
                "title": "Album",
                "year": 2024,
                "is_active": 1,
                "added_at": (now - timedelta(days=15)).isoformat(),
            },
        ])
    finally:
        conn.close()
    
    # Last 3 days - only today
    result = run_recent_releases(days=3, limit=10)
    assert result["count"] == 1
    
    # Last 7 days - today and 5 days ago
    result = run_recent_releases(days=7, limit=10)
    assert result["count"] == 2
    
    # Last 30 days - all three
    result = run_recent_releases(days=30, limit=10)
    assert result["count"] == 3
