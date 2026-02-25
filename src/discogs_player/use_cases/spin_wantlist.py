"""Spin/random wantlist selection use-case."""

from __future__ import annotations

import random

from discogs_player.core.settings import set_setting
from discogs_player.data.db import get_connection
from discogs_player.data.repo import query_wantlist
from discogs_player.use_cases.list_releases import parse_year_range


class NoWantlistItemsFoundError(ValueError):
    """Raised when no wantlist items match the spin filters."""


def run_spin_wantlist(
    *,
    q: str | None = None,
    year: str | None = None,
    genres: list[str] | None = None,
    styles: list[str] | None = None,
    unmatched: bool = False,
    seed: int | None = None,
) -> dict[str, object]:
    year_range = parse_year_range(year)

    conn = get_connection()
    try:
        candidates = query_wantlist(
            conn,
            q=q,
            year_from=year_range.start,
            year_to=year_range.end,
            genres=genres,
            styles=styles,
            limit=None,
            include_market=True,
            unmatched=unmatched,
        )
        if not candidates:
            raise NoWantlistItemsFoundError(
                "No wantlist items found for the provided filters."
            )

        rng = random.Random(seed)
        chosen = rng.choice(candidates)
        set_setting(
            "last_spin_wantlist_id", str(chosen["discogs_release_id"]), conn=conn
        )
        return chosen
    finally:
        conn.close()
