"""Market value status use-case for collection totals/coverage."""

from __future__ import annotations

from discogs_player.data.db import get_connection
from discogs_player.data.repo import get_market_value_summary


def run_market_value_status() -> dict[str, object]:
    conn = get_connection()
    try:
        return get_market_value_summary(conn)
    finally:
        conn.close()
