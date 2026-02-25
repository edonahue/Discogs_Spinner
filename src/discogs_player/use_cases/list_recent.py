
"""Recently added releases use case."""

from __future__ import annotations

from typing import Any

from discogs_player.data.db import get_connection
from discogs_player.data.repo import _attach_market_fields, _row_to_release


def run_recent_releases(
    *,
    days: int = 7,
    limit: int | None = 10,
    include_market: bool = True,
) -> dict[str, Any]:
    """Get recently added releases from the collection.
    
    Args:
        days: Number of days to look back (default: 7)
        limit: Maximum number of releases to return (default: 10)
        include_market: Whether to include market price data
        
    Returns:
        Dictionary with releases list and metadata
    """
    conn = get_connection()
    try:
        # Query releases added within the last N days
        # Use a more efficient query that filters by date
        select_columns = [
            "r.discogs_release_id",
            "r.artist",
            "r.title",
            "r.year",
            "r.genres",
            "r.styles",
            "r.thumb_url",
            "r.cover_url",
            "r.added_at",
            "r.last_synced_at",
            "r.is_active",
            "m.spotify_album_id",
        ]
        
        if include_market:
            select_columns.extend([
                "mp.lowest AS market_lowest",
                "mp.median AS market_median",
                "mp.highest AS market_highest",
                "mp.currency AS market_currency",
                "mp.last_updated_at AS market_last_updated_at",
            ])
        
        sql = f"""
            SELECT {', '.join(select_columns)}
            FROM releases r
            LEFT JOIN spotify_mapping m
              ON m.discogs_release_id = r.discogs_release_id
        """
        
        if include_market:
            sql += """
                LEFT JOIN market_prices mp
                  ON mp.discogs_release_id = r.discogs_release_id
            """
        
        sql += """
            WHERE r.is_active = 1
            AND r.added_at >= date('now', '-' || ? || ' days')
            ORDER BY r.added_at DESC, LOWER(r.artist), LOWER(r.title)
        """
        
        params = [days]
        
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        
        rows = conn.execute(sql, params).fetchall()
        
        if include_market:
            releases = [_attach_market_fields(_row_to_release(row), row) for row in rows]
        else:
            releases = [_row_to_release(row) for row in rows]
        
        return {
            "ok": True,
            "releases": releases,
            "count": len(releases),
            "days": days,
            "limit": limit,
        }
    finally:
        conn.close()
