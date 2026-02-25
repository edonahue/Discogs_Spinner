from __future__ import annotations

import pytest

from discogs_player.data.db import get_connection
from discogs_player.data.repo import (
    get_release_tracklist,
    query_tracklist_refresh_candidates,
    replace_release_tracks,
    upsert_releases,
)
from discogs_player.services.discogs_client import DiscogsApiError
from discogs_player.use_cases import tracklist_refresh, tracklist_show
from discogs_player.use_cases.tracklist_cached import run_release_tracklist_cached
from discogs_player.use_cases.tracklist_refresh import run_refresh_release_tracklists
from discogs_player.use_cases.tracklist_show import run_release_tracklist_show


def _release(release_id: int, *, is_active: int = 1) -> dict[str, object]:
    return {
        "discogs_release_id": release_id,
        "artist": f"Artist {release_id}",
        "title": f"Album {release_id}",
        "year": 2000,
        "genres": ["Rock"],
        "styles": ["Alt"],
        "thumb_url": None,
        "cover_url": None,
        "added_at": "2026-01-01T00:00:00Z",
        "last_synced_at": "2026-01-01T00:00:00Z",
        "is_active": is_active,
    }


def test_release_tracklist_repo_replace_and_get(isolated_xdg):
    conn = get_connection()
    try:
        upsert_releases(conn, [_release(10)])
        replace_release_tracks(
            conn,
            discogs_release_id=10,
            tracks=[
                {
                    "position": "A1",
                    "title": "Opening Track",
                    "duration": "4:05",
                    "type": "track",
                    "is_audio_track": True,
                },
                {
                    "position": "",
                    "title": "Side A",
                    "duration": "",
                    "type": "heading",
                    "is_audio_track": False,
                },
            ],
            last_refreshed_at="2026-02-08T00:00:00+00:00",
        )
        payload = get_release_tracklist(conn, 10)
    finally:
        conn.close()

    assert payload["discogs_release_id"] == 10
    assert payload["track_count"] == 2
    assert payload["audio_track_count"] == 1
    assert payload["has_cached_tracklist"] is True
    assert payload["tracks"][0]["position"] == "A1"
    assert payload["tracks"][0]["is_audio_track"] is True
    assert payload["tracks"][1]["type"] == "heading"


def test_release_tracklist_cached_reads_cache_without_refresh(isolated_xdg):
    conn = get_connection()
    try:
        upsert_releases(conn, [_release(15)])
        replace_release_tracks(
            conn,
            discogs_release_id=15,
            tracks=[
                {
                    "position": "A1",
                    "title": "Cache Hit",
                    "duration": "3:21",
                    "type": "track",
                    "is_audio_track": True,
                }
            ],
            last_refreshed_at="2026-02-08T00:00:00+00:00",
        )
    finally:
        conn.close()

    cached = run_release_tracklist_cached(15)
    assert cached["has_cached_tracklist"] is True
    assert cached["has_tracklist"] is True
    assert cached["has_audio_tracks"] is True
    assert cached["tracks"][0]["title"] == "Cache Hit"


def test_query_tracklist_refresh_candidates_supports_missing_and_stale(isolated_xdg):
    conn = get_connection()
    try:
        upsert_releases(conn, [_release(1), _release(2), _release(3)])
        replace_release_tracks(
            conn,
            discogs_release_id=1,
            tracks=[
                {
                    "position": "A1",
                    "title": "Fresh",
                    "duration": "3:00",
                    "type": "track",
                }
            ],
            last_refreshed_at="2026-02-08T00:00:00+00:00",
        )
        replace_release_tracks(
            conn,
            discogs_release_id=2,
            tracks=[
                {
                    "position": "A1",
                    "title": "Stale",
                    "duration": "3:00",
                    "type": "track",
                }
            ],
            last_refreshed_at="2026-01-01T00:00:00+00:00",
        )
        missing = query_tracklist_refresh_candidates(conn, stale_before=None, limit=10)
        stale = query_tracklist_refresh_candidates(
            conn,
            stale_before="2026-02-01T00:00:00+00:00",
            limit=10,
        )
    finally:
        conn.close()

    assert missing == [3]
    assert stale == [2, 3]


def test_refresh_release_tracklists_updates_rows_and_collects_errors(
    isolated_xdg, monkeypatch
):
    conn = get_connection()
    try:
        upsert_releases(conn, [_release(11), _release(12), _release(13, is_active=0)])
    finally:
        conn.close()

    monkeypatch.setenv("DISCOGS_TOKEN", "token")

    class _FakeClient:
        def __init__(self, token: str):
            self.token = token

        def fetch_release_tracklist(self, release_id: int) -> dict[str, object]:
            if release_id == 12:
                raise DiscogsApiError("Discogs request failed (404): not found")
            return {
                "discogs_release_id": release_id,
                "tracks": [
                    {
                        "position": "A1",
                        "title": f"Track {release_id}",
                        "duration": "4:00",
                        "type": "track",
                        "is_audio_track": True,
                    }
                ],
            }

    monkeypatch.setattr(tracklist_refresh, "DiscogsClient", _FakeClient)
    summary = run_refresh_release_tracklists(limit=10, stale_days=30, from_missing=True)

    assert summary["candidate_count"] == 2
    assert summary["refreshed_count"] == 1
    assert summary["with_audio_track_count"] == 1
    assert summary["without_audio_track_count"] == 0
    assert summary["error_count"] == 1
    assert summary["updated_release_ids"] == [11]
    assert summary["failed_release_ids"] == [12]

    conn = get_connection()
    try:
        cached = get_release_tracklist(conn, 11)
    finally:
        conn.close()
    assert cached["track_count"] == 1
    assert cached["audio_track_count"] == 1


def test_release_tracklist_show_supports_refresh(isolated_xdg, monkeypatch):
    conn = get_connection()
    try:
        upsert_releases(conn, [_release(21)])
    finally:
        conn.close()

    monkeypatch.setenv("DISCOGS_TOKEN", "token")

    class _FakeClient:
        def __init__(self, token: str):
            self.token = token

        def fetch_release_tracklist(self, release_id: int) -> dict[str, object]:
            return {
                "discogs_release_id": release_id,
                "tracks": [
                    {
                        "position": "A1",
                        "title": "Song One",
                        "duration": "5:00",
                        "type": "track",
                        "is_audio_track": True,
                    }
                ],
            }

    monkeypatch.setattr(tracklist_show, "DiscogsClient", _FakeClient)

    before = run_release_tracklist_show(21)
    assert before["track_count"] == 0
    assert before["has_cached_tracklist"] is False

    refreshed = run_release_tracklist_show(21, refresh=True)
    assert refreshed["track_count"] == 1
    assert refreshed["audio_track_count"] == 1
    assert refreshed["has_cached_tracklist"] is True
    assert refreshed["has_audio_tracks"] is True
    assert refreshed["tracks"][0]["title"] == "Song One"


def test_refresh_release_tracklists_validates_inputs():
    with pytest.raises(ValueError, match="limit must be >= 1"):
        run_refresh_release_tracklists(limit=0)
    with pytest.raises(ValueError, match="stale_days must be >= 0"):
        run_refresh_release_tracklists(stale_days=-1)
    with pytest.raises(ValueError, match="Cannot combine from_missing=True"):
        run_refresh_release_tracklists(release_ids=[1], from_missing=True)
