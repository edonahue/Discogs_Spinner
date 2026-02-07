"""Repository helpers for release and mapping data."""

from __future__ import annotations

import json
from typing import Any, Iterable, Sequence


def _to_json_array(value: Any) -> str:
    if value is None:
        return "[]"
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return json.dumps(value)
    return json.dumps([str(value)])


def _row_to_release(row) -> dict[str, Any]:
    try:
        genres = json.loads(row["genres"] or "[]")
    except json.JSONDecodeError:
        genres = []

    try:
        styles = json.loads(row["styles"] or "[]")
    except json.JSONDecodeError:
        styles = []

    return {
        "discogs_release_id": row["discogs_release_id"],
        "artist": row["artist"],
        "title": row["title"],
        "year": row["year"],
        "genres": genres,
        "styles": styles,
        "thumb_url": row["thumb_url"],
        "cover_url": row["cover_url"],
        "added_at": row["added_at"],
        "last_synced_at": row["last_synced_at"],
        "is_active": bool(row["is_active"]),
        "spotify_album_id": row["spotify_album_id"],
    }


def upsert_releases(conn, releases: Iterable[dict[str, Any]]) -> int:
    rows = []
    for release in releases:
        rows.append(
            {
                "discogs_release_id": int(release["discogs_release_id"]),
                "artist": release.get("artist"),
                "title": release.get("title"),
                "year": release.get("year"),
                "genres": _to_json_array(release.get("genres")),
                "styles": _to_json_array(release.get("styles")),
                "thumb_url": release.get("thumb_url"),
                "cover_url": release.get("cover_url"),
                "added_at": release.get("added_at"),
                "last_synced_at": release.get("last_synced_at"),
                "is_active": int(release.get("is_active", 1)),
            }
        )

    if not rows:
        return 0

    conn.executemany(
        """
        INSERT INTO releases(
            discogs_release_id, artist, title, year,
            genres, styles, thumb_url, cover_url,
            added_at, last_synced_at, is_active
        ) VALUES (
            :discogs_release_id, :artist, :title, :year,
            :genres, :styles, :thumb_url, :cover_url,
            :added_at, :last_synced_at, :is_active
        )
        ON CONFLICT(discogs_release_id) DO UPDATE SET
            artist = excluded.artist,
            title = excluded.title,
            year = excluded.year,
            genres = excluded.genres,
            styles = excluded.styles,
            thumb_url = excluded.thumb_url,
            cover_url = excluded.cover_url,
            added_at = excluded.added_at,
            last_synced_at = excluded.last_synced_at,
            is_active = excluded.is_active
        """,
        rows,
    )
    conn.commit()
    return len(rows)


def mark_releases_inactive_missing(conn, active_ids: Sequence[int]) -> int:
    if not active_ids:
        cursor = conn.execute("UPDATE releases SET is_active = 0 WHERE is_active = 1")
        conn.commit()
        return cursor.rowcount

    placeholders = ", ".join(["?"] * len(active_ids))
    sql = (
        f"UPDATE releases SET is_active = 0 "
        f"WHERE is_active = 1 AND discogs_release_id NOT IN ({placeholders})"
    )
    cursor = conn.execute(sql, list(active_ids))
    conn.commit()
    return cursor.rowcount


def query_releases(
    conn,
    *,
    q: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    genres: Sequence[str] | None = None,
    styles: Sequence[str] | None = None,
    limit: int = 25,
    unmatched: bool = False,
) -> list[dict[str, Any]]:
    sql = [
        """
        SELECT
            r.discogs_release_id,
            r.artist,
            r.title,
            r.year,
            r.genres,
            r.styles,
            r.thumb_url,
            r.cover_url,
            r.added_at,
            r.last_synced_at,
            r.is_active,
            m.spotify_album_id
        FROM releases r
        LEFT JOIN spotify_mapping m
          ON m.discogs_release_id = r.discogs_release_id
        WHERE r.is_active = 1
        """
    ]
    params: list[Any] = []

    if q:
        sql.append("AND (LOWER(r.artist) LIKE ? OR LOWER(r.title) LIKE ?)")
        pattern = f"%{q.lower()}%"
        params.extend([pattern, pattern])

    if year_from is not None:
        sql.append("AND r.year >= ?")
        params.append(year_from)

    if year_to is not None:
        sql.append("AND r.year <= ?")
        params.append(year_to)

    if genres:
        for genre in genres:
            sql.append("AND LOWER(r.genres) LIKE ?")
            params.append(f'%"{genre.lower()}"%')

    if styles:
        for style in styles:
            sql.append("AND LOWER(r.styles) LIKE ?")
            params.append(f'%"{style.lower()}"%')

    if unmatched:
        sql.append("AND (m.spotify_album_id IS NULL OR m.spotify_album_id = '')")

    sql.append("ORDER BY LOWER(r.artist), LOWER(r.title)")
    sql.append("LIMIT ?")
    params.append(max(1, int(limit)))

    rows = conn.execute("\n".join(sql), params).fetchall()
    return [_row_to_release(row) for row in rows]


def get_release_counts(conn) -> dict[str, int]:
    total = conn.execute("SELECT COUNT(*) FROM releases").fetchone()[0]
    active = conn.execute("SELECT COUNT(*) FROM releases WHERE is_active = 1").fetchone()[0]
    mapped = conn.execute(
        """
        SELECT COUNT(*)
        FROM releases r
        JOIN spotify_mapping m ON m.discogs_release_id = r.discogs_release_id
        WHERE r.is_active = 1 AND m.spotify_album_id IS NOT NULL AND m.spotify_album_id <> ''
        """
    ).fetchone()[0]
    unmatched = max(int(active) - int(mapped), 0)
    return {
        "release_count_total": int(total),
        "release_count_active": int(active),
        "mapped_count": int(mapped),
        "unmatched_count": int(unmatched),
    }
