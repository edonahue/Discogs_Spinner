"""Build status report payload for CLI/UI surfaces."""

from __future__ import annotations

from discogs_player.core.settings import get_int_setting, get_setting
from discogs_player.data.db import get_connection
from discogs_player.data.repo import (
    get_market_value_last_updated,
    get_release_counts,
    get_wantlist_count,
)


def get_status_report() -> dict[str, object]:
    conn = get_connection()
    try:
        counts = get_release_counts(conn)
        wantlist_count = get_wantlist_count(conn)
        market_value_last_updated = get_market_value_last_updated(conn)
        last_sync_time = get_setting("last_sync_time", conn=conn)
        last_spin_release_id = get_int_setting("last_spin_release_id", conn=conn)
        default_device_id = get_setting("default_spotify_device_id", conn=conn)
        default_device_name = get_setting("default_spotify_device_name", conn=conn)
    finally:
        conn.close()

    return {
        **counts,
        "last_sync_time": last_sync_time,
        "default_spotify_device": {
            "id": default_device_id,
            "name": default_device_name,
        },
        "last_spin_release_id": last_spin_release_id,
        "market_value_last_updated": market_value_last_updated,
        "wantlist_count": wantlist_count,
    }
