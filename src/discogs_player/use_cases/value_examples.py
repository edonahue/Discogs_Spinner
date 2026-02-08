"""Select high/low priced collection examples for CLI/GUI display."""

from __future__ import annotations

from discogs_player.data.db import get_connection
from discogs_player.data.repo import query_market_value_examples


def run_market_value_examples(*, limit: int = 2) -> dict[str, object]:
    if limit < 1:
        raise ValueError("limit must be >= 1")

    conn = get_connection()
    try:
        examples = query_market_value_examples(conn, limit=limit)
    finally:
        conn.close()

    return {
        "limit": int(limit),
        "high_priced": examples["high_priced"],
        "low_priced": examples["low_priced"],
    }
