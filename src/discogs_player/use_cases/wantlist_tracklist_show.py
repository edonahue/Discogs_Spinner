"""Show cached Discogs wantlist tracklist details for one release."""

from __future__ import annotations

from datetime import datetime, timezone

from discogs_player.core.settings import (
    discogs_token_missing_message,
    get_discogs_token,
)
from discogs_player.data.db import get_connection
from discogs_player.data.repo import (
    get_wantlist_by_id,
    get_wantlist_tracklist,
    replace_wantlist_tracks,
)
from discogs_player.services.discogs_client import DiscogsClient
from discogs_player.services.sync_manager import MissingDiscogsTokenError


def run_wantlist_tracklist_show(
    release_id: int, *, refresh: bool = False
) -> dict[str, object]:
    normalized_release_id = int(release_id)
    if normalized_release_id <= 0:
        raise ValueError("release_id must be a positive integer")

    conn = get_connection()
    try:
        entry = get_wantlist_by_id(conn, normalized_release_id, include_market=True)
        if entry is None:
            raise ValueError(f"Wantlist release not found: {normalized_release_id}")
        cached = get_wantlist_tracklist(conn, normalized_release_id)
    finally:
        conn.close()

    if refresh:
        token = get_discogs_token()
        if not token:
            raise MissingDiscogsTokenError(discogs_token_missing_message())

        payload = DiscogsClient(token=token).fetch_release_tracklist(
            normalized_release_id
        )
        tracks_raw = payload.get("tracks")
        tracks = (
            [item for item in tracks_raw if isinstance(item, dict)]
            if isinstance(tracks_raw, list)
            else []
        )
        now_iso = datetime.now(timezone.utc).isoformat()

        conn = get_connection()
        try:
            replace_wantlist_tracks(
                conn,
                discogs_release_id=normalized_release_id,
                tracks=tracks,
                last_refreshed_at=now_iso,
            )
            cached = get_wantlist_tracklist(conn, normalized_release_id)
            entry = (
                get_wantlist_by_id(conn, normalized_release_id, include_market=True)
                or entry
            )
        finally:
            conn.close()

    result = dict(entry)
    result["tracks"] = cached.get("tracks")
    result["track_count"] = int(cached.get("track_count") or 0)
    result["audio_track_count"] = int(cached.get("audio_track_count") or 0)
    result["tracklist_last_refreshed_at"] = cached.get("last_refreshed_at")
    result["has_cached_tracklist"] = bool(cached.get("has_cached_tracklist"))
    result["has_tracklist"] = result["track_count"] > 0
    result["has_audio_tracks"] = result["audio_track_count"] > 0
    return result
