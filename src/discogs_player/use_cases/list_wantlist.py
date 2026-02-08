"""List wantlist entries use-case boundary."""

from __future__ import annotations

from discogs_player.data.db import get_connection
from discogs_player.data.repo import query_wantlist
from discogs_player.use_cases.list_releases import parse_year_range


def run_list_wantlist(
    *,
    limit: int = 25,
    q: str | None = None,
    year: str | None = None,
    genres: list[str] | None = None,
    styles: list[str] | None = None,
    with_value: bool = False,
) -> list[dict[str, object]]:
    year_range = parse_year_range(year)

    conn = get_connection()
    try:
        return query_wantlist(
            conn,
            q=q,
            year_from=year_range.start,
            year_to=year_range.end,
            genres=genres,
            styles=styles,
            limit=limit,
            include_market=with_value,
        )
    finally:
        conn.close()
