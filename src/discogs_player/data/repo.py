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


def _attach_market_fields(item: dict[str, Any], row) -> dict[str, Any]:
    item["market_lowest"] = row["market_lowest"]
    item["market_median"] = row["market_median"]
    item["market_highest"] = row["market_highest"]
    item["market_currency"] = row["market_currency"]
    item["market_last_updated_at"] = row["market_last_updated_at"]

    # Attach new stats if present in row
    if "num_for_sale" in row.keys():
        item["num_for_sale"] = row["num_for_sale"]
        item["lowest_price"] = row["lowest_price"]
        item["community_have"] = row["community_have"]
        item["community_want"] = row["community_want"]
        item["rating_count"] = row["rating_count"]
        item["rating_average"] = row["rating_average"]

    return item


def _row_to_release_export(row) -> dict[str, Any]:
    item = _row_to_release(row)
    item["spotify_confidence"] = row["spotify_confidence"]
    item["spotify_last_checked_at"] = row["spotify_last_checked_at"]
    item["spotify_is_override"] = bool(row["spotify_is_override"])
    return _attach_market_fields(item, row)


def _row_to_mapping(row) -> dict[str, Any]:
    return {
        "discogs_release_id": row["discogs_release_id"],
        "spotify_album_id": row["spotify_album_id"],
        "confidence": row["confidence"],
        "last_checked_at": row["last_checked_at"],
        "is_override": bool(row["is_override"]),
    }


def _row_to_wantlist(row) -> dict[str, Any]:
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
        "notes": row["notes"],
        "added_at": row["added_at"],
        "last_synced_at": row["last_synced_at"],
        "is_active": bool(row["is_active"]),
        "spotify_album_id": row["spotify_album_id"],
    }


def get_wantlist_by_id(
    conn,
    discogs_release_id: int,
    *,
    include_market: bool = False,
) -> dict[str, Any] | None:
    select_columns = [
        "w.discogs_release_id",
        "w.artist",
        "w.title",
        "w.year",
        "w.genres",
        "w.styles",
        "w.thumb_url",
        "w.cover_url",
        "w.notes",
        "w.added_at",
        "w.last_synced_at",
        "w.is_active",
        "m.spotify_album_id",
    ]
    if include_market:
        select_columns.extend(
            [
                "COALESCE(wmp.lowest, mp.lowest) AS market_lowest",
                "COALESCE(wmp.median, mp.median) AS market_median",
                "COALESCE(wmp.highest, mp.highest) AS market_highest",
                "COALESCE(wmp.currency, mp.currency) AS market_currency",
                "COALESCE(wmp.last_updated_at, mp.last_updated_at) AS market_last_updated_at",
                # New stats columns
                "ws.num_for_sale",
                "ws.lowest_price",
                "ws.community_have",
                "ws.community_want",
                "ws.rating_count",
                "ws.rating_average",
            ]
        )

    sql = [
        f"""
        SELECT
            {", ".join(select_columns)}
        FROM wantlist w
        LEFT JOIN spotify_mapping m
          ON m.discogs_release_id = w.discogs_release_id
        """
    ]
    if include_market:
        sql.append(
            """
            LEFT JOIN wantlist_market_prices wmp
              ON wmp.discogs_release_id = w.discogs_release_id
            LEFT JOIN market_prices mp
              ON mp.discogs_release_id = w.discogs_release_id
            LEFT JOIN wantlist_stats ws
              ON ws.discogs_release_id = w.discogs_release_id
            """
        )
    sql.append("WHERE w.discogs_release_id = ?")
    row = conn.execute("\n".join(sql), (int(discogs_release_id),)).fetchone()
    if row is None:
        return None
    base = _row_to_wantlist(row)
    if include_market:
        return _attach_market_fields(base, row)
    return base


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


def get_release_by_id(
    conn,
    discogs_release_id: int,
    *,
    include_market: bool = False,
) -> dict[str, Any] | None:
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
        select_columns.extend(
            [
                "mp.lowest AS market_lowest",
                "mp.median AS market_median",
                "mp.highest AS market_highest",
                "mp.currency AS market_currency",
                "mp.last_updated_at AS market_last_updated_at",
                "rs.num_for_sale",
                "rs.lowest_price",
                "rs.community_have",
                "rs.community_want",
                "rs.rating_count",
                "rs.rating_average",
            ]
        )

    sql = [
        f"""
        SELECT
            {", ".join(select_columns)}
        FROM releases r
        LEFT JOIN spotify_mapping m
          ON m.discogs_release_id = r.discogs_release_id
        """
    ]
    if include_market:
        sql.append(
            """
            LEFT JOIN market_prices mp
              ON mp.discogs_release_id = r.discogs_release_id
            LEFT JOIN release_stats rs
              ON rs.discogs_release_id = r.discogs_release_id
            """
        )
    sql.append("WHERE r.discogs_release_id = ?")

    row = conn.execute("\n".join(sql), (discogs_release_id,)).fetchone()
    if row is None:
        return None
    base = _row_to_release(row)
    if include_market:
        return _attach_market_fields(base, row)
    return base


def get_spotify_mapping(conn, discogs_release_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT discogs_release_id, spotify_album_id, confidence, last_checked_at, is_override
        FROM spotify_mapping
        WHERE discogs_release_id = ?
        """,
        (discogs_release_id,),
    ).fetchone()
    if row is None:
        return None
    return _row_to_mapping(row)


def upsert_spotify_mapping(
    conn,
    *,
    discogs_release_id: int,
    spotify_album_id: str | None,
    confidence: float | None,
    last_checked_at: str | None,
    is_override: bool = False,
    provider_id: str = "spotify",
    commit: bool = True,
) -> None:
    conn.execute(
        """
        INSERT INTO spotify_mapping(
            discogs_release_id, spotify_album_id, confidence, last_checked_at, is_override,
            provider_id
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(discogs_release_id) DO UPDATE SET
            spotify_album_id = excluded.spotify_album_id,
            confidence = excluded.confidence,
            last_checked_at = excluded.last_checked_at,
            is_override = excluded.is_override,
            provider_id = excluded.provider_id
        """,
        (
            int(discogs_release_id),
            spotify_album_id,
            confidence,
            last_checked_at,
            1 if is_override else 0,
            str(provider_id) if provider_id else "spotify",
        ),
    )
    if commit:
        conn.commit()


def query_releases(
    conn,
    *,
    q: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    genres: Sequence[str] | None = None,
    styles: Sequence[str] | None = None,
    limit: int | None = 25,
    unmatched: bool = False,
    include_market: bool = False,
) -> list[dict[str, Any]]:
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
        select_columns.extend(
            [
                "mp.lowest AS market_lowest",
                "mp.median AS market_median",
                "mp.highest AS market_highest",
                "mp.currency AS market_currency",
                "mp.last_updated_at AS market_last_updated_at",
                # New stats columns
                "rs.num_for_sale",
                "rs.lowest_price",
                "rs.community_have",
                "rs.community_want",
                "rs.rating_count",
                "rs.rating_average",
            ]
        )

    sql = [
        f"""
        SELECT
            {", ".join(select_columns)}
        FROM releases r
        LEFT JOIN spotify_mapping m
          ON m.discogs_release_id = r.discogs_release_id
        """
    ]
    if include_market:
        sql.append(
            """
            LEFT JOIN market_prices mp
              ON mp.discogs_release_id = r.discogs_release_id
            LEFT JOIN release_stats rs
              ON rs.discogs_release_id = r.discogs_release_id
            """
        )
    sql.append("WHERE r.is_active = 1")
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
    if limit is not None:
        sql.append("LIMIT ?")
        params.append(max(1, int(limit)))

    rows = conn.execute("\n".join(sql), params).fetchall()
    if include_market:
        return [_attach_market_fields(_row_to_release(row), row) for row in rows]
    return [_row_to_release(row) for row in rows]


def query_releases_for_export(
    conn,
    *,
    include_inactive: bool = True,
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
            m.spotify_album_id,
            m.confidence AS spotify_confidence,
            m.last_checked_at AS spotify_last_checked_at,
            COALESCE(m.is_override, 0) AS spotify_is_override,
            mp.lowest AS market_lowest,
            mp.median AS market_median,
            mp.highest AS market_highest,
            mp.currency AS market_currency,
            mp.last_updated_at AS market_last_updated_at
        FROM releases r
        LEFT JOIN spotify_mapping m
          ON m.discogs_release_id = r.discogs_release_id
        LEFT JOIN market_prices mp
          ON mp.discogs_release_id = r.discogs_release_id
        """
    ]
    params: list[Any] = []

    if not include_inactive:
        sql.append("WHERE r.is_active = 1")

    sql.append("ORDER BY LOWER(r.artist), LOWER(r.title), r.discogs_release_id")

    rows = conn.execute("\n".join(sql), params).fetchall()
    return [_row_to_release_export(row) for row in rows]


def get_release_counts(conn) -> dict[str, int]:
    total = conn.execute("SELECT COUNT(*) FROM releases").fetchone()[0]
    active = conn.execute(
        "SELECT COUNT(*) FROM releases WHERE is_active = 1"
    ).fetchone()[0]
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


def get_wantlist_counts(conn) -> dict[str, int]:
    total = conn.execute("SELECT COUNT(*) FROM wantlist").fetchone()[0]
    active = conn.execute(
        "SELECT COUNT(*) FROM wantlist WHERE is_active = 1"
    ).fetchone()[0]
    mapped = conn.execute(
        """
        SELECT COUNT(*)
        FROM wantlist w
        JOIN spotify_mapping m ON m.discogs_release_id = w.discogs_release_id
        WHERE w.is_active = 1 AND m.spotify_album_id IS NOT NULL AND m.spotify_album_id <> ''
        """
    ).fetchone()[0]
    unmatched = max(int(active) - int(mapped), 0)
    return {
        "wantlist_count_total": int(total),
        "wantlist_count_active": int(active),
        "wantlist_mapped_count": int(mapped),
        "wantlist_unmatched_count": int(unmatched),
    }


def upsert_wantlist_entries(conn, entries: Iterable[dict[str, Any]]) -> int:
    rows = []
    for entry in entries:
        rows.append(
            {
                "discogs_release_id": int(entry["discogs_release_id"]),
                "artist": entry.get("artist"),
                "title": entry.get("title"),
                "year": entry.get("year"),
                "genres": _to_json_array(entry.get("genres")),
                "styles": _to_json_array(entry.get("styles")),
                "thumb_url": entry.get("thumb_url"),
                "cover_url": entry.get("cover_url"),
                "notes": entry.get("notes"),
                "added_at": entry.get("added_at"),
                "last_synced_at": entry.get("last_synced_at"),
                "is_active": int(entry.get("is_active", 1)),
            }
        )

    if not rows:
        return 0

    conn.executemany(
        """
        INSERT INTO wantlist(
            discogs_release_id, artist, title, year,
            genres, styles, thumb_url, cover_url,
            notes, added_at, last_synced_at, is_active
        ) VALUES (
            :discogs_release_id, :artist, :title, :year,
            :genres, :styles, :thumb_url, :cover_url,
            :notes, :added_at, :last_synced_at, :is_active
        )
        ON CONFLICT(discogs_release_id) DO UPDATE SET
            artist = excluded.artist,
            title = excluded.title,
            year = excluded.year,
            genres = excluded.genres,
            styles = excluded.styles,
            thumb_url = excluded.thumb_url,
            cover_url = excluded.cover_url,
            notes = excluded.notes,
            added_at = excluded.added_at,
            last_synced_at = excluded.last_synced_at,
            is_active = excluded.is_active
        """,
        rows,
    )
    conn.commit()
    return len(rows)


def mark_wantlist_inactive_missing(conn, active_ids: Sequence[int]) -> int:
    if not active_ids:
        cursor = conn.execute("UPDATE wantlist SET is_active = 0 WHERE is_active = 1")
        conn.commit()
        return cursor.rowcount

    placeholders = ", ".join(["?"] * len(active_ids))
    sql = (
        f"UPDATE wantlist SET is_active = 0 "
        f"WHERE is_active = 1 AND discogs_release_id NOT IN ({placeholders})"
    )
    cursor = conn.execute(sql, list(active_ids))
    conn.commit()
    return cursor.rowcount


def query_wantlist(
    conn,
    *,
    q: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    genres: Sequence[str] | None = None,
    styles: Sequence[str] | None = None,
    limit: int | None = 25,
    include_market: bool = False,
    unmatched: bool = False,
) -> list[dict[str, Any]]:
    select_columns = [
        "w.discogs_release_id",
        "w.artist",
        "w.title",
        "w.year",
        "w.genres",
        "w.styles",
        "w.thumb_url",
        "w.cover_url",
        "w.notes",
        "w.added_at",
        "w.last_synced_at",
        "w.is_active",
        "m.spotify_album_id",
    ]
    if include_market:
        select_columns.extend(
            [
                "COALESCE(wmp.lowest, mp.lowest) AS market_lowest",
                "COALESCE(wmp.median, mp.median) AS market_median",
                "COALESCE(wmp.highest, mp.highest) AS market_highest",
                "COALESCE(wmp.currency, mp.currency) AS market_currency",
                "COALESCE(wmp.last_updated_at, mp.last_updated_at) AS market_last_updated_at",
                # New stats columns
                "ws.num_for_sale",
                "ws.lowest_price",
                "ws.community_have",
                "ws.community_want",
                "ws.rating_count",
                "ws.rating_average",
            ]
        )

    sql = [
        f"""
        SELECT
            {", ".join(select_columns)}
        FROM wantlist w
        LEFT JOIN spotify_mapping m
          ON m.discogs_release_id = w.discogs_release_id
        """
    ]
    if include_market:
        sql.append(
            """
            LEFT JOIN wantlist_market_prices wmp
              ON wmp.discogs_release_id = w.discogs_release_id
            LEFT JOIN market_prices mp
              ON mp.discogs_release_id = w.discogs_release_id
            LEFT JOIN wantlist_stats ws
              ON ws.discogs_release_id = w.discogs_release_id
            """
        )
    sql.append("WHERE w.is_active = 1")
    params: list[Any] = []

    if q:
        sql.append("AND (LOWER(w.artist) LIKE ? OR LOWER(w.title) LIKE ?)")
        pattern = f"%{q.lower()}%"
        params.extend([pattern, pattern])

    if year_from is not None:
        sql.append("AND w.year >= ?")
        params.append(year_from)

    if year_to is not None:
        sql.append("AND w.year <= ?")
        params.append(year_to)

    if genres:
        for genre in genres:
            sql.append("AND LOWER(w.genres) LIKE ?")
            params.append(f'%"{genre.lower()}"%')

    if styles:
        for style in styles:
            sql.append("AND LOWER(w.styles) LIKE ?")
            params.append(f'%"{style.lower()}"%')

    if unmatched:
        sql.append("AND (m.spotify_album_id IS NULL OR m.spotify_album_id = '')")

    sql.append("ORDER BY LOWER(w.artist), LOWER(w.title), w.discogs_release_id")
    if limit is not None:
        sql.append("LIMIT ?")
        params.append(max(1, int(limit)))

    rows = conn.execute("\n".join(sql), params).fetchall()
    if include_market:
        return [_attach_market_fields(_row_to_wantlist(row), row) for row in rows]
    return [_row_to_wantlist(row) for row in rows]


def get_wantlist_count(conn) -> int:
    row = conn.execute("SELECT COUNT(*) FROM wantlist WHERE is_active = 1").fetchone()
    return int(row[0]) if row else 0


def upsert_wantlist_market_price(
    conn,
    *,
    discogs_release_id: int,
    lowest: float | None,
    median: float | None,
    highest: float | None,
    currency: str | None,
    last_updated_at: str | None,
    commit: bool = True,
) -> None:
    conn.execute(
        """
        INSERT INTO wantlist_market_prices(
            discogs_release_id, lowest, median, highest, currency, last_updated_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(discogs_release_id) DO UPDATE SET
            lowest = excluded.lowest,
            median = excluded.median,
            highest = excluded.highest,
            currency = excluded.currency,
            last_updated_at = excluded.last_updated_at
        """,
        (
            int(discogs_release_id),
            lowest,
            median,
            highest,
            currency,
            last_updated_at,
        ),
    )
    if commit:
        conn.commit()


def replace_wantlist_tracks(
    conn,
    *,
    discogs_release_id: int,
    tracks: Sequence[dict[str, Any]],
    last_refreshed_at: str,
    commit: bool = True,
) -> None:
    normalized_release_id = int(discogs_release_id)
    if normalized_release_id <= 0:
        raise ValueError("discogs_release_id must be a positive integer")
    if not last_refreshed_at:
        raise ValueError("last_refreshed_at is required")

    normalized_rows: list[dict[str, Any]] = []
    audio_track_count = 0
    for seq, track in enumerate(tracks, start=1):
        if not isinstance(track, dict):
            continue
        position = str(track.get("position") or "").strip() or None
        title = str(track.get("title") or "").strip() or None
        duration = str(track.get("duration") or "").strip() or None
        track_type = str(track.get("type") or track.get("type_") or "").strip() or None
        is_audio_track = bool(track.get("is_audio_track"))
        if not is_audio_track and isinstance(track_type, str):
            is_audio_track = track_type.lower() == "track" and bool(title)
        if is_audio_track:
            audio_track_count += 1
        normalized_rows.append(
            {
                "discogs_release_id": normalized_release_id,
                "seq": seq,
                "position": position,
                "title": title,
                "duration": duration,
                "type": track_type,
                "is_audio_track": 1 if is_audio_track else 0,
            }
        )

    conn.execute(
        "DELETE FROM wantlist_tracks WHERE discogs_release_id = ?",
        (normalized_release_id,),
    )
    if normalized_rows:
        conn.executemany(
            """
            INSERT INTO wantlist_tracks(
                discogs_release_id,
                seq,
                position,
                title,
                duration,
                type,
                is_audio_track
            ) VALUES (
                :discogs_release_id,
                :seq,
                :position,
                :title,
                :duration,
                :type,
                :is_audio_track
            )
            """,
            normalized_rows,
        )
    conn.execute(
        """
        INSERT INTO wantlist_tracklist_cache(
            discogs_release_id,
            track_count,
            audio_track_count,
            last_refreshed_at
        ) VALUES (?, ?, ?, ?)
        ON CONFLICT(discogs_release_id) DO UPDATE SET
            track_count = excluded.track_count,
            audio_track_count = excluded.audio_track_count,
            last_refreshed_at = excluded.last_refreshed_at
        """,
        (
            normalized_release_id,
            len(normalized_rows),
            audio_track_count,
            last_refreshed_at,
        ),
    )
    if commit:
        conn.commit()


def get_wantlist_tracklist(conn, discogs_release_id: int) -> dict[str, Any]:
    normalized_release_id = int(discogs_release_id)
    if normalized_release_id <= 0:
        raise ValueError("discogs_release_id must be a positive integer")

    cache_row = conn.execute(
        """
        SELECT discogs_release_id, track_count, audio_track_count, last_refreshed_at
        FROM wantlist_tracklist_cache
        WHERE discogs_release_id = ?
        """,
        (normalized_release_id,),
    ).fetchone()

    track_rows = conn.execute(
        """
        SELECT discogs_release_id, seq, position, title, duration, type, is_audio_track
        FROM wantlist_tracks
        WHERE discogs_release_id = ?
        ORDER BY seq ASC
        """,
        (normalized_release_id,),
    ).fetchall()

    tracks = [
        {
            "discogs_release_id": int(row["discogs_release_id"]),
            "seq": int(row["seq"]),
            "position": row["position"],
            "title": row["title"],
            "duration": row["duration"],
            "type": row["type"],
            "is_audio_track": bool(row["is_audio_track"]),
        }
        for row in track_rows
    ]

    return {
        "discogs_release_id": normalized_release_id,
        "track_count": int(cache_row["track_count"]) if cache_row else 0,
        "audio_track_count": int(cache_row["audio_track_count"]) if cache_row else 0,
        "last_refreshed_at": str(cache_row["last_refreshed_at"]) if cache_row else None,
        "has_cached_tracklist": bool(cache_row is not None),
        "tracks": tracks,
    }


def upsert_market_price(
    conn,
    *,
    discogs_release_id: int,
    lowest: float | None,
    median: float | None,
    highest: float | None,
    currency: str | None,
    last_updated_at: str | None,
    commit: bool = True,
) -> None:
    conn.execute(
        """
        INSERT INTO market_prices(
            discogs_release_id, lowest, median, highest, currency, last_updated_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(discogs_release_id) DO UPDATE SET
            lowest = excluded.lowest,
            median = excluded.median,
            highest = excluded.highest,
            currency = excluded.currency,
            last_updated_at = excluded.last_updated_at
        """,
        (
            int(discogs_release_id),
            lowest,
            median,
            highest,
            currency,
            last_updated_at,
        ),
    )
    if commit:
        conn.commit()


def get_market_price(conn, discogs_release_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT discogs_release_id, lowest, median, highest, currency, last_updated_at
        FROM market_prices
        WHERE discogs_release_id = ?
        """,
        (discogs_release_id,),
    ).fetchone()
    if row is None:
        return None
    return {
        "discogs_release_id": row["discogs_release_id"],
        "lowest": row["lowest"],
        "median": row["median"],
        "highest": row["highest"],
        "currency": row["currency"],
        "last_updated_at": row["last_updated_at"],
    }


def query_market_price_refresh_candidates(
    conn,
    *,
    stale_before: str | None = None,
    limit: int | None = None,
) -> list[int]:
    sql = [
        """
        SELECT r.discogs_release_id
        FROM releases r
        LEFT JOIN market_prices mp
          ON mp.discogs_release_id = r.discogs_release_id
        WHERE r.is_active = 1
        """
    ]
    params: list[Any] = []

    if stale_before is None:
        sql.append("AND mp.discogs_release_id IS NULL")
    else:
        sql.append(
            """
            AND (
                mp.discogs_release_id IS NULL
                OR mp.last_updated_at IS NULL
                OR mp.last_updated_at < ?
            )
            """
        )
        params.append(stale_before)

    sql.append("ORDER BY LOWER(r.artist), LOWER(r.title), r.discogs_release_id")
    if limit is not None:
        sql.append("LIMIT ?")
        params.append(max(1, int(limit)))

    rows = conn.execute("\n".join(sql), params).fetchall()
    return [int(row["discogs_release_id"]) for row in rows]


def query_releases_missing_market_values(
    conn,
    *,
    limit: int | None = 25,
) -> list[dict[str, Any]]:
    return query_releases_needing_market_refresh(
        conn,
        limit=limit,
        stale_before=None,
        include_market=False,
    )


def query_releases_needing_market_refresh(
    conn,
    *,
    limit: int | None = 25,
    stale_before: str | None = None,
    include_market: bool = False,
) -> list[dict[str, Any]]:
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
        """
        CASE
            WHEN mp.discogs_release_id IS NULL THEN 'missing'
            WHEN (mp.lowest IS NULL AND mp.median IS NULL AND mp.highest IS NULL) THEN 'unpriced'
            WHEN (? IS NOT NULL AND (mp.last_updated_at IS NULL OR mp.last_updated_at < ?)) THEN 'stale'
            ELSE 'unknown'
        END AS market_need_reason
        """.strip(),
    ]
    if include_market:
        select_columns.extend(
            [
                "mp.lowest AS market_lowest",
                "mp.median AS market_median",
                "mp.highest AS market_highest",
                "mp.currency AS market_currency",
                "mp.last_updated_at AS market_last_updated_at",
            ]
        )

    sql = [
        """
        SELECT
        """
        + ",\n            ".join(select_columns)
        + """
        FROM releases r
        LEFT JOIN spotify_mapping m
          ON m.discogs_release_id = r.discogs_release_id
        LEFT JOIN market_prices mp
          ON mp.discogs_release_id = r.discogs_release_id
        WHERE r.is_active = 1
          AND (
              mp.discogs_release_id IS NULL
              OR (mp.lowest IS NULL AND mp.median IS NULL AND mp.highest IS NULL)
              OR (? IS NOT NULL AND (mp.last_updated_at IS NULL OR mp.last_updated_at < ?))
          )
        ORDER BY LOWER(r.artist), LOWER(r.title), r.discogs_release_id
        """
    ]
    params: list[Any] = [stale_before, stale_before, stale_before, stale_before]
    if limit is not None:
        sql.append("LIMIT ?")
        params.append(max(1, int(limit)))

    rows = conn.execute("\n".join(sql), params).fetchall()
    if include_market:
        return [
            _attach_market_fields(
                {
                    **_row_to_release(row),
                    "market_need_reason": row["market_need_reason"],
                },
                row,
            )
            for row in rows
        ]
    return [
        {**_row_to_release(row), "market_need_reason": row["market_need_reason"]}
        for row in rows
    ]


def get_market_value_last_updated(conn) -> str | None:
    row = conn.execute(
        """
        SELECT MAX(mp.last_updated_at)
        FROM releases r
        JOIN market_prices mp
          ON mp.discogs_release_id = r.discogs_release_id
        WHERE r.is_active = 1
        """
    ).fetchone()
    if row is None:
        return None
    value = row[0]
    return str(value) if value else None


def _row_to_market_example(row) -> dict[str, Any]:
    artist = str(row["artist"] or "").strip() or "Unknown Artist"
    title = str(row["title"] or "").strip() or "Unknown Title"
    return {
        "discogs_release_id": int(row["discogs_release_id"]),
        "artist": artist,
        "title": title,
        "release_display": f"{artist} - {title}",
        "market_lowest": row["market_lowest"],
        "market_median": row["market_median"],
        "market_highest": row["market_highest"],
        "market_currency": row["market_currency"],
        "market_last_updated_at": row["market_last_updated_at"],
    }


def query_market_value_examples(
    conn,
    *,
    limit: int = 2,
) -> dict[str, list[dict[str, Any]]]:
    normalized_limit = max(1, int(limit))

    select_sql = """
        SELECT
            r.discogs_release_id,
            r.artist,
            r.title,
            mp.lowest AS market_lowest,
            mp.median AS market_median,
            mp.highest AS market_highest,
            mp.currency AS market_currency,
            mp.last_updated_at AS market_last_updated_at
        FROM releases r
        JOIN market_prices mp
          ON mp.discogs_release_id = r.discogs_release_id
        WHERE r.is_active = 1
          AND mp.median IS NOT NULL
    """

    high_rows = conn.execute(
        select_sql
        + """
        ORDER BY mp.median DESC, LOWER(r.artist), LOWER(r.title), r.discogs_release_id
        LIMIT ?
        """,
        (normalized_limit,),
    ).fetchall()

    low_rows = conn.execute(
        select_sql
        + """
        ORDER BY mp.median ASC, LOWER(r.artist), LOWER(r.title), r.discogs_release_id
        LIMIT ?
        """,
        (normalized_limit,),
    ).fetchall()

    return {
        "high_priced": [_row_to_market_example(row) for row in high_rows],
        "low_priced": [_row_to_market_example(row) for row in low_rows],
    }


def get_market_value_summary(conn) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT
            COUNT(*) AS active_release_count,
            SUM(
                CASE
                    WHEN mp.lowest IS NOT NULL OR mp.median IS NOT NULL OR mp.highest IS NOT NULL
                    THEN 1
                    ELSE 0
                END
            ) AS priced_release_count,
            SUM(COALESCE(mp.lowest, 0.0)) AS total_lowest,
            SUM(COALESCE(mp.median, 0.0)) AS total_median,
            SUM(COALESCE(mp.highest, 0.0)) AS total_highest,
            MAX(mp.last_updated_at) AS market_value_last_updated
        FROM releases r
        LEFT JOIN market_prices mp
          ON mp.discogs_release_id = r.discogs_release_id
        WHERE r.is_active = 1
        """
    ).fetchone()

    active_release_count = int(row["active_release_count"] or 0) if row else 0
    priced_release_count = int(row["priced_release_count"] or 0) if row else 0

    currency_rows = conn.execute(
        """
        SELECT mp.currency AS currency, COUNT(*) AS count
        FROM releases r
        JOIN market_prices mp
          ON mp.discogs_release_id = r.discogs_release_id
        WHERE r.is_active = 1
          AND mp.currency IS NOT NULL
          AND mp.currency <> ''
          AND (mp.lowest IS NOT NULL OR mp.median IS NOT NULL OR mp.highest IS NOT NULL)
        GROUP BY mp.currency
        ORDER BY count DESC, mp.currency ASC
        """
    ).fetchall()

    currency_counts = [
        {"currency": str(item["currency"]), "count": int(item["count"])}
        for item in currency_rows
    ]

    return {
        "active_release_count": active_release_count,
        "priced_release_count": priced_release_count,
        "unpriced_release_count": max(active_release_count - priced_release_count, 0),
        "total_lowest": float(row["total_lowest"] or 0.0) if row else 0.0,
        "total_median": float(row["total_median"] or 0.0) if row else 0.0,
        "total_highest": float(row["total_highest"] or 0.0) if row else 0.0,
        "market_value_last_updated": str(row["market_value_last_updated"])
        if row and row["market_value_last_updated"]
        else None,
        "currency_counts": currency_counts,
    }


def insert_market_value_snapshot(
    conn,
    *,
    captured_at: str,
    active_release_count: int,
    priced_release_count: int,
    unpriced_release_count: int,
    total_lowest: float,
    total_median: float,
    total_highest: float,
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO market_value_snapshots(
            captured_at,
            active_release_count,
            priced_release_count,
            unpriced_release_count,
            total_lowest,
            total_median,
            total_highest
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            captured_at,
            int(active_release_count),
            int(priced_release_count),
            int(unpriced_release_count),
            float(total_lowest),
            float(total_median),
            float(total_highest),
        ),
    )
    conn.commit()
    return int(cursor.lastrowid)


def query_market_value_snapshots(
    conn,
    *,
    limit: int | None = 30,
) -> list[dict[str, Any]]:
    sql = [
        """
        SELECT
            id,
            captured_at,
            active_release_count,
            priced_release_count,
            unpriced_release_count,
            total_lowest,
            total_median,
            total_highest
        FROM market_value_snapshots
        ORDER BY captured_at DESC, id DESC
        """
    ]
    params: list[Any] = []
    if limit is not None:
        sql.append("LIMIT ?")
        params.append(max(1, int(limit)))

    rows = conn.execute("\n".join(sql), params).fetchall()
    return [
        {
            "id": int(row["id"]),
            "captured_at": str(row["captured_at"]),
            "active_release_count": int(row["active_release_count"]),
            "priced_release_count": int(row["priced_release_count"]),
            "unpriced_release_count": int(row["unpriced_release_count"]),
            "total_lowest": float(row["total_lowest"] or 0.0),
            "total_median": float(row["total_median"] or 0.0),
            "total_highest": float(row["total_highest"] or 0.0),
        }
        for row in rows
    ]


def replace_release_tracks(
    conn,
    *,
    discogs_release_id: int,
    tracks: Sequence[dict[str, Any]],
    last_refreshed_at: str,
    commit: bool = True,
) -> None:
    normalized_release_id = int(discogs_release_id)
    if normalized_release_id <= 0:
        raise ValueError("discogs_release_id must be a positive integer")
    if not last_refreshed_at:
        raise ValueError("last_refreshed_at is required")

    normalized_rows: list[dict[str, Any]] = []
    audio_track_count = 0
    for seq, track in enumerate(tracks, start=1):
        if not isinstance(track, dict):
            continue
        position = str(track.get("position") or "").strip() or None
        title = str(track.get("title") or "").strip() or None
        duration = str(track.get("duration") or "").strip() or None
        track_type = str(track.get("type") or track.get("type_") or "").strip() or None
        is_audio_track = bool(track.get("is_audio_track"))
        if not is_audio_track and isinstance(track_type, str):
            is_audio_track = track_type.lower() == "track" and bool(title)
        if is_audio_track:
            audio_track_count += 1
        normalized_rows.append(
            {
                "discogs_release_id": normalized_release_id,
                "seq": seq,
                "position": position,
                "title": title,
                "duration": duration,
                "type": track_type,
                "is_audio_track": 1 if is_audio_track else 0,
            }
        )

    conn.execute(
        "DELETE FROM release_tracks WHERE discogs_release_id = ?",
        (normalized_release_id,),
    )
    if normalized_rows:
        conn.executemany(
            """
            INSERT INTO release_tracks(
                discogs_release_id,
                seq,
                position,
                title,
                duration,
                type,
                is_audio_track
            ) VALUES (
                :discogs_release_id,
                :seq,
                :position,
                :title,
                :duration,
                :type,
                :is_audio_track
            )
            """,
            normalized_rows,
        )
    conn.execute(
        """
        INSERT INTO release_tracklist_cache(
            discogs_release_id,
            track_count,
            audio_track_count,
            last_refreshed_at
        ) VALUES (?, ?, ?, ?)
        ON CONFLICT(discogs_release_id) DO UPDATE SET
            track_count = excluded.track_count,
            audio_track_count = excluded.audio_track_count,
            last_refreshed_at = excluded.last_refreshed_at
        """,
        (
            normalized_release_id,
            len(normalized_rows),
            audio_track_count,
            last_refreshed_at,
        ),
    )
    if commit:
        conn.commit()


def get_release_tracklist(conn, discogs_release_id: int) -> dict[str, Any]:
    normalized_release_id = int(discogs_release_id)
    if normalized_release_id <= 0:
        raise ValueError("discogs_release_id must be a positive integer")

    cache_row = conn.execute(
        """
        SELECT discogs_release_id, track_count, audio_track_count, last_refreshed_at
        FROM release_tracklist_cache
        WHERE discogs_release_id = ?
        """,
        (normalized_release_id,),
    ).fetchone()

    track_rows = conn.execute(
        """
        SELECT discogs_release_id, seq, position, title, duration, type, is_audio_track
        FROM release_tracks
        WHERE discogs_release_id = ?
        ORDER BY seq ASC
        """,
        (normalized_release_id,),
    ).fetchall()

    tracks = [
        {
            "discogs_release_id": int(row["discogs_release_id"]),
            "seq": int(row["seq"]),
            "position": row["position"],
            "title": row["title"],
            "duration": row["duration"],
            "type": row["type"],
            "is_audio_track": bool(row["is_audio_track"]),
        }
        for row in track_rows
    ]

    return {
        "discogs_release_id": normalized_release_id,
        "track_count": int(cache_row["track_count"]) if cache_row else 0,
        "audio_track_count": int(cache_row["audio_track_count"]) if cache_row else 0,
        "last_refreshed_at": str(cache_row["last_refreshed_at"]) if cache_row else None,
        "has_cached_tracklist": bool(cache_row is not None),
        "tracks": tracks,
    }


def query_tracklist_refresh_candidates(
    conn,
    *,
    stale_before: str | None = None,
    limit: int | None = None,
) -> list[int]:
    sql = [
        """
        SELECT r.discogs_release_id
        FROM releases r
        LEFT JOIN release_tracklist_cache rtc
          ON rtc.discogs_release_id = r.discogs_release_id
        WHERE r.is_active = 1
        """
    ]
    params: list[Any] = []

    if stale_before is None:
        sql.append("AND rtc.discogs_release_id IS NULL")
    else:
        sql.append(
            """
            AND (
                rtc.discogs_release_id IS NULL
                OR rtc.last_refreshed_at IS NULL
                OR rtc.last_refreshed_at < ?
            )
            """
        )
        params.append(stale_before)

    sql.append("ORDER BY LOWER(r.artist), LOWER(r.title), r.discogs_release_id")
    if limit is not None:
        sql.append("LIMIT ?")
        params.append(max(1, int(limit)))

    rows = conn.execute("\n".join(sql), params).fetchall()
    return [int(row["discogs_release_id"]) for row in rows]
