"""Compute a collection data-quality health score.

Score: 0–100. Deductions applied per gap bucket:
  - missing market price  (-20 max, proportional)
  - missing year          (-20 max, proportional)
  - missing genres        (-20 max, proportional)
  - missing cover art     (-20 max, proportional)
  - unmatched (Spotify)   (-20 max, proportional) — only if Spotify capable

Each bucket is capped at its maximum deduction so one very bad signal
cannot drive the score below 0.
"""

from __future__ import annotations

from discogs_player.data.db import get_connection


def _pct(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator * 100.0, 1)


def _deduction(gap_count: int, total: int, max_deduction: float) -> float:
    if total == 0:
        return 0.0
    return min(max_deduction, gap_count / total * max_deduction)


def run_collection_health() -> dict[str, object]:
    """Compute and return a collection health score with per-bucket breakdown.

    Returns:
        Dict with ``score`` (0–100 int), ``total_active``, and ``buckets``
        list of dicts (name, gap_count, gap_pct, max_deduction, deduction).
    """
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total_active,
                SUM(CASE
                    WHEN mp.discogs_release_id IS NULL
                      OR (mp.lowest IS NULL AND mp.median IS NULL AND mp.highest IS NULL)
                    THEN 1 ELSE 0 END) AS missing_price,
                SUM(CASE
                    WHEN r.year IS NULL OR r.year <= 0
                    THEN 1 ELSE 0 END) AS missing_year,
                SUM(CASE
                    WHEN r.genres IS NULL OR r.genres = '' OR r.genres = '[]'
                    THEN 1 ELSE 0 END) AS missing_genres,
                SUM(CASE
                    WHEN (r.cover_url IS NULL OR r.cover_url = '')
                      AND (r.thumb_url IS NULL OR r.thumb_url = '')
                    THEN 1 ELSE 0 END) AS missing_cover,
                SUM(CASE
                    WHEN sm.spotify_album_id IS NULL OR sm.spotify_album_id = ''
                    THEN 1 ELSE 0 END) AS unmatched_spotify
            FROM releases r
            LEFT JOIN market_prices mp
              ON mp.discogs_release_id = r.discogs_release_id
            LEFT JOIN spotify_mapping sm
              ON sm.discogs_release_id = r.discogs_release_id
            WHERE r.is_active = 1
            """
        ).fetchone()
    finally:
        conn.close()

    total = int(row["total_active"] or 0)
    missing_price = int(row["missing_price"] or 0)
    missing_year = int(row["missing_year"] or 0)
    missing_genres = int(row["missing_genres"] or 0)
    missing_cover = int(row["missing_cover"] or 0)
    unmatched = int(row["unmatched_spotify"] or 0)

    buckets = [
        {
            "name": "missing_price",
            "label": "Missing market price",
            "gap_count": missing_price,
            "gap_pct": _pct(missing_price, total),
            "max_deduction": 20.0,
            "deduction": _deduction(missing_price, total, 20.0),
        },
        {
            "name": "missing_year",
            "label": "Missing release year",
            "gap_count": missing_year,
            "gap_pct": _pct(missing_year, total),
            "max_deduction": 20.0,
            "deduction": _deduction(missing_year, total, 20.0),
        },
        {
            "name": "missing_genres",
            "label": "Missing genre/style tags",
            "gap_count": missing_genres,
            "gap_pct": _pct(missing_genres, total),
            "max_deduction": 20.0,
            "deduction": _deduction(missing_genres, total, 20.0),
        },
        {
            "name": "missing_cover",
            "label": "Missing cover art",
            "gap_count": missing_cover,
            "gap_pct": _pct(missing_cover, total),
            "max_deduction": 20.0,
            "deduction": _deduction(missing_cover, total, 20.0),
        },
        {
            "name": "unmatched_spotify",
            "label": "Unmatched (Spotify)",
            "gap_count": unmatched,
            "gap_pct": _pct(unmatched, total),
            "max_deduction": 20.0,
            "deduction": _deduction(unmatched, total, 20.0),
        },
    ]

    total_deduction = sum(
        float(b["deduction"]) if isinstance(b["deduction"], (int, float)) else 0.0
        for b in buckets
    )
    score = max(0, round(100.0 - total_deduction))

    return {
        "score": score,
        "total_active": total,
        "buckets": buckets,
    }
