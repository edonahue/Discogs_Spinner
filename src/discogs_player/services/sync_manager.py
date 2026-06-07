"""Orchestrates Discogs fetch + local persistence."""

from __future__ import annotations

from datetime import datetime, timezone
import threading
from typing import Callable

from discogs_player.core.settings import (
    discogs_token_missing_message,
    get_discogs_token,
    set_setting,
)
from discogs_player.data.db import get_connection
from discogs_player.data.repo import (
    get_wantlist_count,
    get_release_counts,
    mark_wantlist_inactive_missing,
    mark_releases_inactive_missing,
    upsert_wantlist_entries,
    upsert_releases,
)
from discogs_player.services.discogs_client import DiscogsClient

ProgressCallback = Callable[[int, int, int, int], None]


class MissingDiscogsTokenError(RuntimeError):
    """Raised when Discogs token is not configured."""


class SyncCancelledError(RuntimeError):
    """Raised when a sync is cancelled via cancel_token."""


def _extract_active_release_ids(items: list[dict[str, object]]) -> list[int]:
    release_ids: list[int] = []
    for item in items:
        release_id = item.get("discogs_release_id")
        if isinstance(release_id, int):
            release_ids.append(release_id)
    return release_ids


def sync_collection(
    *,
    progress_callback: ProgressCallback | None = None,
    allow_empty_deactivate: bool = False,
    cancel_token: threading.Event | None = None,
) -> dict[str, object]:
    token = get_discogs_token()
    if not token:
        raise MissingDiscogsTokenError(discogs_token_missing_message())

    client = DiscogsClient(token=token)
    releases = client.fetch_collection_releases(
        progress_callback=progress_callback,
        cancel_token=cancel_token,
    )

    conn = get_connection()
    try:
        upserted_count = upsert_releases(conn, releases)
        active_ids = _extract_active_release_ids(releases)
        counts_before_deactivate = get_release_counts(conn)
        existing_active_count = counts_before_deactivate["release_count_active"]
        warnings: list[str] = []

        if active_ids or allow_empty_deactivate or existing_active_count == 0:
            deactivated_count = mark_releases_inactive_missing(conn, active_ids)
        else:
            deactivated_count = 0
            warnings.append(
                "Discogs returned zero releases; skipped soft-delete to protect local data. "
                "Re-run with --full to allow empty soft-delete."
            )

        last_sync_time = datetime.now(timezone.utc).isoformat()
        set_setting("last_sync_time", last_sync_time, conn=conn)
    finally:
        conn.close()

    return {
        "fetched_count": len(releases),
        "upserted_count": upserted_count,
        "deactivated_count": deactivated_count,
        "last_sync_time": last_sync_time,
        "skipped_empty_deactivate": bool(warnings),
        "warnings": warnings,
    }


def sync_wantlist(
    *,
    progress_callback: ProgressCallback | None = None,
    allow_empty_deactivate: bool = False,
) -> dict[str, object]:
    token = get_discogs_token()
    if not token:
        raise MissingDiscogsTokenError(discogs_token_missing_message())

    client = DiscogsClient(token=token)
    entries = client.fetch_wantlist_releases(progress_callback=progress_callback)

    conn = get_connection()
    try:
        upserted_count = upsert_wantlist_entries(conn, entries)
        active_ids = _extract_active_release_ids(entries)
        existing_active_count = get_wantlist_count(conn)
        warnings: list[str] = []

        if active_ids or allow_empty_deactivate or existing_active_count == 0:
            deactivated_count = mark_wantlist_inactive_missing(conn, active_ids)
        else:
            deactivated_count = 0
            warnings.append(
                "Discogs returned zero wantlist releases; skipped soft-delete to protect local data. "
                "Re-run with --full to allow empty soft-delete."
            )

        last_sync_time = datetime.now(timezone.utc).isoformat()
        set_setting("last_wantlist_sync_time", last_sync_time, conn=conn)
    finally:
        conn.close()

    return {
        "fetched_count": len(entries),
        "upserted_count": upserted_count,
        "deactivated_count": deactivated_count,
        "last_sync_time": last_sync_time,
        "skipped_empty_deactivate": bool(warnings),
        "warnings": warnings,
    }
