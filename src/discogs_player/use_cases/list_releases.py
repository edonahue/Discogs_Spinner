"""List releases use-case boundary."""

from __future__ import annotations

from dataclasses import dataclass

from discogs_player.data.db import get_connection
from discogs_player.data.repo import query_releases


@dataclass
class YearRange:
    start: int | None
    end: int | None


def _parse_year_value(raw: str, *, original_input: str) -> int:
    value = raw.strip()
    if not value:
        raise ValueError(
            f"Invalid year range '{original_input}'. Use YYYY or YYYY:YYYY (start/end optional)."
        )
    if not value.isdigit():
        raise ValueError(
            f"Invalid year range '{original_input}'. Use YYYY or YYYY:YYYY (start/end optional)."
        )
    return int(value)


def parse_year_range(raw: str | None) -> YearRange:
    if not raw:
        return YearRange(start=None, end=None)

    raw = raw.strip()
    if not raw:
        return YearRange(start=None, end=None)

    if ":" in raw:
        left, right = raw.split(":", 1)
        start = _parse_year_value(left, original_input=raw) if left else None
        end = _parse_year_value(right, original_input=raw) if right else None

        if start is None and end is None:
            raise ValueError(
                f"Invalid year range '{raw}'. Use YYYY or YYYY:YYYY (start/end optional)."
            )
        if start is not None and end is not None and start > end:
            raise ValueError("Year range must be start:end with start <= end")
        return YearRange(start=start, end=end)

    year = _parse_year_value(raw, original_input=raw)
    return YearRange(start=year, end=year)


def run_list_releases(
    *,
    limit: int = 25,
    q: str | None = None,
    year: str | None = None,
    genres: list[str] | None = None,
    styles: list[str] | None = None,
    unmatched: bool = False,
    with_value: bool = False,
) -> list[dict[str, object]]:
    year_range = parse_year_range(year)

    conn = get_connection()
    try:
        return query_releases(
            conn,
            q=q,
            year_from=year_range.start,
            year_to=year_range.end,
            genres=genres,
            styles=styles,
            limit=limit,
            unmatched=unmatched,
            include_market=with_value,
        )
    finally:
        conn.close()
