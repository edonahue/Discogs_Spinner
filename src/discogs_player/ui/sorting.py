"""Shared sorting helpers for GUI release browsing."""

from __future__ import annotations


def _as_int(value: object | None) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped and stripped.lstrip("-").isdigit():
            return int(stripped)
    return 0


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
                -_as_int(item.get("year")),
                str(item.get("artist") or "").lower(),
                str(item.get("title") or "").lower(),
            ),
        )
    if normalized == "year_asc":
        return sorted(
            items,
            key=lambda item: (
                item.get("year") is None,
                _as_int(item.get("year")),
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
                -_as_int(item.get("year")),
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
