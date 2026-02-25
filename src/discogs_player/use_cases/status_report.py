"""Build status report payload for CLI/UI surfaces."""

from __future__ import annotations

from discogs_player.capabilities import get_capabilities
from discogs_player.core.settings import get_int_setting, get_setting
from discogs_player.data.db import get_connection
from discogs_player.data.repo import (
    get_market_value_last_updated,
    get_release_counts,
    get_wantlist_counts,
    get_wantlist_count,
)


def get_status_report() -> dict[str, object]:
    capabilities = get_capabilities().spotify
    conn = get_connection()
    try:
        counts = get_release_counts(conn)
        wantlist_counts = get_wantlist_counts(conn)
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
        **wantlist_counts,
        "last_sync_time": last_sync_time,
        "default_spotify_device": {
            "id": default_device_id,
            "name": default_device_name,
        },
        "spotify_capability": {
            "addon_available": capabilities.addon_available,
            "configured": capabilities.configured,
            "action_label": capabilities.action_label,
            "status_message": capabilities.status_message,
        },
        "last_spin_release_id": last_spin_release_id,
        "market_value_last_updated": market_value_last_updated,
        # Backward-compatible alias for existing CLI/UI consumers.
        "wantlist_count": wantlist_count,
    }
