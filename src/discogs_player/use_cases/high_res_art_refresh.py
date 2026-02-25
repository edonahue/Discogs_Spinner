"""Optional collection pipeline to pre-warm higher-resolution Discogs cover art."""

from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Literal

from discogs_player.data.db import get_connection
from discogs_player.services.high_res_art import (
    get_high_res_art_preference,
    normalize_high_res_art_target_size,
    upgrade_discogs_cover_url,
)
from discogs_player.services.image_cache import get_or_fetch_cover_path

HighResArtScope = Literal["collection", "wantlist", "both"]
_MAX_WORKERS = 16


def _normalize_scope(scope: str) -> HighResArtScope:
    normalized = str(scope or "").strip().casefold()
    if normalized in {"collection", "wantlist", "both"}:
        return normalized  # type: ignore[return-value]
    raise ValueError("scope must be one of: collection, wantlist, both")


def _normalize_limit(limit: int | None) -> int | None:
    if limit is None:
        return None
    parsed = int(limit)
    if parsed <= 0:
        raise ValueError("limit must be a positive integer")
    return parsed


def _normalize_workers(workers: int) -> int:
    parsed = int(workers)
    if parsed <= 0:
        raise ValueError("workers must be a positive integer")
    return min(_MAX_WORKERS, parsed)


def _query_collection_rows(conn, *, limit: int | None) -> list[tuple[str, int, str]]:
    sql = [
        """
        SELECT discogs_release_id, cover_url
        FROM releases
        WHERE is_active = 1
          AND cover_url IS NOT NULL
          AND cover_url <> ''
        ORDER BY discogs_release_id
        """
    ]
    params: list[object] = []
    if limit is not None:
        sql.append("LIMIT ?")
        params.append(limit)

    rows = conn.execute("\n".join(sql), params).fetchall()
    return [
        ("collection", int(row["discogs_release_id"]), str(row["cover_url"]))
        for row in rows
    ]


def _query_wantlist_rows(conn, *, limit: int | None) -> list[tuple[str, int, str]]:
    sql = [
        """
        SELECT discogs_release_id, cover_url
        FROM wantlist
        WHERE is_active = 1
          AND cover_url IS NOT NULL
          AND cover_url <> ''
        ORDER BY discogs_release_id
        """
    ]
    params: list[object] = []
    if limit is not None:
        sql.append("LIMIT ?")
        params.append(limit)

    rows = conn.execute("\n".join(sql), params).fetchall()
    return [("wantlist", int(row["discogs_release_id"]), str(row["cover_url"])) for row in rows]


def _query_scope_rows(
    conn,
    *,
    scope: HighResArtScope,
    limit: int | None,
) -> list[tuple[str, int, str]]:
    if scope == "collection":
        return _query_collection_rows(conn, limit=limit)
    if scope == "wantlist":
        return _query_wantlist_rows(conn, limit=limit)

    if limit is None:
        return _query_collection_rows(conn, limit=None) + _query_wantlist_rows(
            conn, limit=None
        )

    remaining = int(limit)
    rows: list[tuple[str, int, str]] = []
    if remaining > 0:
        collection_rows = _query_collection_rows(conn, limit=remaining)
        rows.extend(collection_rows)
        remaining -= len(collection_rows)
    if remaining > 0:
        rows.extend(_query_wantlist_rows(conn, limit=remaining))
    return rows


def run_refresh_high_res_art(
    *,
    scope: str = "collection",
    limit: int | None = None,
    target_size: int | None = None,
    workers: int = 8,
    dry_run: bool = False,
) -> dict[str, object]:
    normalized_scope = _normalize_scope(scope)
    normalized_limit = _normalize_limit(limit)
    if target_size is None:
        _enabled, configured_target = get_high_res_art_preference()
        normalized_target = normalize_high_res_art_target_size(configured_target)
    else:
        normalized_target = normalize_high_res_art_target_size(target_size)
    normalized_workers = _normalize_workers(workers)

    conn = get_connection()
    try:
        rows = _query_scope_rows(
            conn,
            scope=normalized_scope,
            limit=normalized_limit,
        )
    finally:
        conn.close()

    scoped_counts: Counter[str] = Counter()
    unique_upgraded_url_counts: Counter[str] = Counter()
    unique_fallback_url_counts: Counter[str] = Counter()
    scanned_count = 0
    eligible_count = 0

    for row_scope, _release_id, raw_cover_url in rows:
        scoped_counts[row_scope] += 1
        scanned_count += 1
        upgraded = upgrade_discogs_cover_url(
            raw_cover_url,
            target_size=normalized_target,
        )
        if upgraded and upgraded != raw_cover_url:
            eligible_count += 1
            unique_upgraded_url_counts[upgraded] += 1
            continue
        unique_fallback_url_counts[raw_cover_url] += 1

    combined_url_counts: Counter[str] = Counter()
    combined_url_counts.update(unique_upgraded_url_counts)
    for url, count in unique_fallback_url_counts.items():
        combined_url_counts[url] += int(count)

    unique_upgraded_url_count = len(unique_upgraded_url_counts)
    unique_candidate_url_count = len(combined_url_counts)
    warmed_url_count = 0
    warmed_release_count = 0
    failed_url_count = 0
    fallback_original_url_count = len(unique_fallback_url_counts)

    if not dry_run and unique_candidate_url_count > 0:
        max_workers = min(normalized_workers, unique_candidate_url_count)
        with ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="high-res-art",
        ) as executor:
            future_to_url = {
                executor.submit(get_or_fetch_cover_path, cover_url): cover_url
                for cover_url in combined_url_counts
            }
            for future in as_completed(future_to_url):
                cover_url = future_to_url[future]
                try:
                    cover_path = future.result()
                except Exception:
                    cover_path = None

                if not cover_path:
                    failed_url_count += 1
                    continue

                warmed_url_count += 1
                warmed_release_count += int(combined_url_counts[cover_url])

    return {
        "scope": normalized_scope,
        "limit": normalized_limit,
        "target_size": normalized_target,
        "workers": normalized_workers,
        "dry_run": bool(dry_run),
        "scanned_count": scanned_count,
        "eligible_count": eligible_count,
        "unique_upgraded_url_count": unique_upgraded_url_count,
        "unique_candidate_url_count": unique_candidate_url_count,
        "fallback_original_url_count": fallback_original_url_count,
        "warmed_url_count": warmed_url_count,
        "failed_url_count": failed_url_count,
        "warmed_release_count": warmed_release_count,
        "collection_scanned_count": int(scoped_counts.get("collection", 0)),
        "wantlist_scanned_count": int(scoped_counts.get("wantlist", 0)),
    }
