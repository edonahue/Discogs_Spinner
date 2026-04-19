"""Fetch a single collection release by Discogs id."""

from __future__ import annotations

from discogs_player.data.db import get_connection
from discogs_player.data.repo import get_release_by_id


def run_get_release(
    discogs_release_id: int,
    *,
    with_value: bool = False,
) -> dict[str, object]:
    normalized_release_id = int(discogs_release_id)
    if normalized_release_id <= 0:
        raise ValueError("discogs_release_id must be a positive integer")

    conn = get_connection()
    try:
        row = get_release_by_id(
            conn,
            normalized_release_id,
            include_market=with_value,
        )
    finally:
        conn.close()

    if row is None:
        raise ValueError(f"Discogs release {normalized_release_id} was not found.")
    return dict(row)
