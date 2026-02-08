"""Shared sorting helpers for GUI release browsing."""

from __future__ import annotations


def _first_genre(item: dict[str, object]) -> str:
    genres = item.get("genres")
    if isinstance(genres, list) and genres:
        return str(genres[0] or "").strip().lower()
    return ""


def sort_release_items(
    items: list[dict[str, object]],
    *,
    sort_mode: str,
) -> list[dict[str, object]]:
    normalized = str(sort_mode or "artist_title").strip().lower()

    if normalized == "year_desc":
        return sorted(
            items,
            key=lambda item: (
                item.get("year") is None,
                -int(item.get("year") or 0),
                str(item.get("artist") or "").lower(),
                str(item.get("title") or "").lower(),
            ),
        )
    if normalized == "year_asc":
        return sorted(
            items,
            key=lambda item: (
                item.get("year") is None,
                int(item.get("year") or 0),
                str(item.get("artist") or "").lower(),
                str(item.get("title") or "").lower(),
            ),
        )
    if normalized == "genre":
        return sorted(
            items,
            key=lambda item: (
                _first_genre(item),
                str(item.get("artist") or "").lower(),
                str(item.get("title") or "").lower(),
            ),
        )
    if normalized == "genre_year":
        return sorted(
            items,
            key=lambda item: (
                _first_genre(item),
                item.get("year") is None,
                -int(item.get("year") or 0),
                str(item.get("artist") or "").lower(),
                str(item.get("title") or "").lower(),
            ),
        )
    return sorted(
        items,
        key=lambda item: (
            str(item.get("artist") or "").lower(),
            str(item.get("title") or "").lower(),
        ),
    )
