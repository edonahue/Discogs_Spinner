"""Collection analytics use-case for local DB data."""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

from discogs_player.data.db import get_connection
from discogs_player.data.repo import query_releases


def _as_str_items(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for raw in value:
        text = str(raw or "").strip()
        if text:
            items.append(text)
    return items


def _as_year(value: Any) -> int | None:
    parsed: int | None = None
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, str):
        text = value.strip()
        if text.isdigit():
            parsed = int(text)

    if parsed is None or parsed <= 0:
        return None
    return parsed


def _extract_iso_year(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if len(text) < 4:
        return None
    year = text[:4]
    if not year.isdigit():
        return None
    return int(year)


def _sorted_year_rows(counter: Counter[int]) -> list[dict[str, int]]:
    return [{"year": year, "count": int(counter[year])} for year in sorted(counter)]


def _sorted_top_rows(
    counter: Counter[str],
    *,
    key_name: str,
    limit: int,
) -> list[dict[str, int | str]]:
    rows = sorted(counter.items(), key=lambda item: (-item[1], item[0].casefold()))
    return [{key_name: key, "count": int(count)} for key, count in rows[:limit]]


def _count_items(counter: Counter[str], values: Iterable[str]) -> None:
    for value in values:
        counter[value] += 1


def run_collection_analytics(*, limit: int = 10) -> dict[str, object]:
    if limit < 1:
        raise ValueError("limit must be >= 1")

    conn = get_connection()
    try:
        releases = query_releases(conn, limit=None)
    finally:
        conn.close()

    mapped_count = 0
    release_year_counter: Counter[int] = Counter()
    added_year_counter: Counter[int] = Counter()
    genre_counter: Counter[str] = Counter()
    style_counter: Counter[str] = Counter()
    artist_counter: Counter[str] = Counter()

    for item in releases:
        if item.get("spotify_album_id"):
            mapped_count += 1

        release_year = _as_year(item.get("year"))
        if release_year is not None:
            release_year_counter[release_year] += 1

        added_year = _extract_iso_year(item.get("added_at"))
        if added_year is not None:
            added_year_counter[added_year] += 1

        _count_items(genre_counter, _as_str_items(item.get("genres")))
        _count_items(style_counter, _as_str_items(item.get("styles")))

        artist = str(item.get("artist") or "").strip()
        if artist:
            artist_counter[artist] += 1

    release_count_active = len(releases)
    unmatched_count = max(release_count_active - mapped_count, 0)

    return {
        "release_count_active": release_count_active,
        "mapped_count": mapped_count,
        "unmatched_count": unmatched_count,
        "top_limit": limit,
        "by_release_year": _sorted_year_rows(release_year_counter),
        "acquisition_timeline": _sorted_year_rows(added_year_counter),
        "top_genres": _sorted_top_rows(genre_counter, key_name="genre", limit=limit),
        "top_styles": _sorted_top_rows(style_counter, key_name="style", limit=limit),
        "top_artists": _sorted_top_rows(artist_counter, key_name="artist", limit=limit),
    }
