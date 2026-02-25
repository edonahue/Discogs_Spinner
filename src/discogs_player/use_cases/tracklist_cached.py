"""Read cached Discogs tracklist rows for UI rendering."""

from __future__ import annotations

from discogs_player.data.db import get_connection
from discogs_player.data.repo import get_release_tracklist


def run_release_tracklist_cached(release_id: int) -> dict[str, object]:
    normalized_release_id = int(release_id)
    if normalized_release_id <= 0:
        raise ValueError("release_id must be a positive integer")

    conn = get_connection()
    try:
        cached = get_release_tracklist(conn, normalized_release_id)
    finally:
        conn.close()

    result = dict(cached)
    track_count = int(result.get("track_count") or 0)
    audio_track_count = int(result.get("audio_track_count") or 0)
    result["has_tracklist"] = track_count > 0
    result["has_audio_tracks"] = audio_track_count > 0
    return result
