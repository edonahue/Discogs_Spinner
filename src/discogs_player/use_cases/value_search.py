"""Search synced collection and wantlist records for the Value workspace."""

from __future__ import annotations

import re

from discogs_player.data.db import get_connection
from discogs_player.data.repo import (
    get_release_by_id,
    get_wantlist_by_id,
    query_releases,
    query_wantlist,
)
from discogs_player.use_cases.value_release_detail import (
    build_value_release_record,
)

_DISCOGS_RELEASE_URL_RE = re.compile(
    r"discogs\.com/(?:[^/]+/)?release/(\d+)",
    flags=re.I,
)


def _parse_discogs_release_query(query: str) -> tuple[str, int | None]:
    normalized = str(query or "").strip()
    if not normalized:
        return "empty", None
    if normalized.isdigit():
        release_id = int(normalized)
        return ("discogs-id", release_id if release_id > 0 else None)
    match = _DISCOGS_RELEASE_URL_RE.search(normalized)
    if match:
        return "discogs-url", int(match.group(1))
    return "text", None


def _normalize_active_result(
    source: str,
    item: dict[str, object] | None,
) -> dict[str, object] | None:
    if not isinstance(item, dict):
        return None
    if not bool(item.get("is_active")):
        return None
    return build_value_release_record(source, item)


def run_search_value_releases(
    query: str | None,
    *,
    limit_per_source: int = 25,
) -> dict[str, object]:
    normalized_limit = max(1, int(limit_per_source))
    normalized_query = str(query or "").strip()
    query_kind, parsed_release_id = _parse_discogs_release_query(normalized_query)

    if not normalized_query:
        return {
            "query": "",
            "query_kind": "empty",
            "parsed_release_id": None,
            "result_count": 0,
            "collection_count": 0,
            "wantlist_count": 0,
            "results": [],
            "unresolved_release_id": None,
            "unresolved_discogs_url": None,
            "unresolved_marketplace_url": None,
        }

    conn = get_connection()
    try:
        if parsed_release_id is not None:
            results: list[dict[str, object]] = []
            collection = _normalize_active_result(
                "collection",
                get_release_by_id(
                    conn,
                    parsed_release_id,
                    include_market=True,
                ),
            )
            if collection is not None:
                results.append(collection)

            wantlist = _normalize_active_result(
                "wantlist",
                get_wantlist_by_id(
                    conn,
                    parsed_release_id,
                    include_market=True,
                ),
            )
            if wantlist is not None:
                results.append(wantlist)
        else:
            collection = [
                build_value_release_record("collection", item)
                for item in query_releases(
                    conn,
                    q=normalized_query,
                    limit=normalized_limit,
                    include_market=True,
                )
            ]
            wantlist = [
                build_value_release_record("wantlist", item)
                for item in query_wantlist(
                    conn,
                    q=normalized_query,
                    limit=normalized_limit,
                    include_market=True,
                )
            ]
            results = sorted(
                [*collection, *wantlist],
                key=lambda item: (
                    str(item.get("artist") or "").lower(),
                    str(item.get("title") or "").lower(),
                    str(item.get("source") or ""),
                    int(item.get("discogs_release_id") or 0),
                ),
            )
    finally:
        conn.close()

    collection_count = sum(1 for item in results if item.get("source") == "collection")
    wantlist_count = sum(1 for item in results if item.get("source") == "wantlist")
    unresolved_release_id = parsed_release_id if parsed_release_id and not results else None

    return {
        "query": normalized_query,
        "query_kind": query_kind,
        "parsed_release_id": parsed_release_id,
        "result_count": len(results),
        "collection_count": collection_count,
        "wantlist_count": wantlist_count,
        "results": results,
        "unresolved_release_id": unresolved_release_id,
        "unresolved_discogs_url": (
            f"https://www.discogs.com/release/{unresolved_release_id}"
            if unresolved_release_id is not None
            else None
        ),
        "unresolved_marketplace_url": (
            f"https://www.discogs.com/sell/release/{unresolved_release_id}"
            if unresolved_release_id is not None
            else None
        ),
    }
