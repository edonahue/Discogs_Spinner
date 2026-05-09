"""Filtered collection summary for browse surfaces."""

from __future__ import annotations

from discogs_player.data.db import get_connection
from discogs_player.data.repo import query_release_summary
from discogs_player.use_cases.list_releases import parse_year_range


def run_release_collection_summary(
    *,
    q: str | None = None,
    year: str | None = None,
    genres: list[str] | None = None,
    styles: list[str] | None = None,
    unmatched: bool = False,
) -> dict[str, object]:
    year_range = parse_year_range(year)

    conn = get_connection()
    try:
        return query_release_summary(
            conn,
            q=q,
            year_from=year_range.start,
            year_to=year_range.end,
            genres=genres,
            styles=styles,
            unmatched=unmatched,
        )
    finally:
        conn.close()
