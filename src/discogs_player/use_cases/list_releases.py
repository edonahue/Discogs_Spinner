"""List releases use-case boundary."""

from __future__ import annotations

from dataclasses import dataclass

from discogs_player.data.db import get_connection
from discogs_player.data.repo import query_releases


@dataclass
class YearRange:
    start: int | None
    end: int | None


def parse_year_range(raw: str | None) -> YearRange:
    if not raw:
        return YearRange(start=None, end=None)

    if ":" in raw:
        left, right = raw.split(":", 1)
        start = int(left) if left else None
        end = int(right) if right else None
        if start is not None and end is not None and start > end:
            raise ValueError("Year range must be start:end with start <= end")
        return YearRange(start=start, end=end)

    year = int(raw)
    return YearRange(start=year, end=year)


def run_list_releases(
    *,
    limit: int = 25,
    q: str | None = None,
    year: str | None = None,
    genres: list[str] | None = None,
    styles: list[str] | None = None,
    unmatched: bool = False,
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
        )
    finally:
        conn.close()
