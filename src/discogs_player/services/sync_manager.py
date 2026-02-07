"""Orchestrates Discogs fetch + local persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from discogs_player.core.settings import get_discogs_token, set_setting
from discogs_player.data.db import get_connection
from discogs_player.data.repo import mark_releases_inactive_missing, upsert_releases
from discogs_player.services.discogs_client import DiscogsClient

ProgressCallback = Callable[[int, int, int, int], None]


class MissingDiscogsTokenError(RuntimeError):
    """Raised when Discogs token is not configured."""


def sync_collection(*, progress_callback: ProgressCallback | None = None) -> dict[str, object]:
    token = get_discogs_token()
    if not token:
        raise MissingDiscogsTokenError(
            "DISCOGS_TOKEN is not set. Export it in your shell or store it in app_settings."
        )

    client = DiscogsClient(token=token)
    releases = client.fetch_collection_releases(progress_callback=progress_callback)

    conn = get_connection()
    try:
        upserted_count = upsert_releases(conn, releases)
        active_ids = [int(item["discogs_release_id"]) for item in releases]
        deactivated_count = mark_releases_inactive_missing(conn, active_ids)
        last_sync_time = datetime.now(timezone.utc).isoformat()
        set_setting("last_sync_time", last_sync_time, conn=conn)
    finally:
        conn.close()

    return {
        "fetched_count": len(releases),
        "upserted_count": upserted_count,
        "deactivated_count": deactivated_count,
        "last_sync_time": last_sync_time,
    }
