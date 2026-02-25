from __future__ import annotations


import pytest

from discogs_player.data.db import get_connection
from discogs_player.data.repo import (
    replace_wantlist_tracks,
    upsert_wantlist_entries,
)
from discogs_player.services.sync_manager import MissingDiscogsTokenError
from discogs_player.use_cases import (
    wantlist_tracklist_cached,
    wantlist_tracklist_show,
    wantlist_value_refresh,
)


def _wantlist_entry(release_id: int) -> dict[str, object]:
    return {
        "discogs_release_id": release_id,
        "artist": f"Artist {release_id}",
        "title": f"Title {release_id}",
        "year": 2020,
        "is_active": 1,
        "added_at": "2026-01-01T00:00:00Z",
        "last_synced_at": "2026-01-01T00:00:00Z",
    }


def test_wantlist_value_refresh_updates_prices(isolated_xdg, monkeypatch):
    conn = get_connection()
    try:
        upsert_wantlist_entries(conn, [_wantlist_entry(100)])
    finally:
        conn.close()

    monkeypatch.setenv("DISCOGS_TOKEN", "token")

    class _FakeClient:
        def __init__(self, token: str):
            pass

        def fetch_market_price_suggestions(self, release_id: int):
            return {
                "lowest": 10.0,
                "median": 15.0,
                "highest": 20.0,
                "currency": "USD",
            }

    monkeypatch.setattr(wantlist_value_refresh, "DiscogsClient", _FakeClient)

    result = wantlist_value_refresh.run_refresh_wantlist_market_value(100)

    assert result["market_median"] == 15.0
    assert result["market_currency"] == "USD"
    assert result["market_last_updated_at"] is not None


def test_wantlist_value_refresh_requires_token(isolated_xdg, monkeypatch):
    monkeypatch.delenv("DISCOGS_TOKEN", raising=False)
    with pytest.raises(MissingDiscogsTokenError):
        wantlist_value_refresh.run_refresh_wantlist_market_value(100)


def test_wantlist_tracklist_cached_returns_empty_if_missing(isolated_xdg):
    conn = get_connection()
    try:
        upsert_wantlist_entries(conn, [_wantlist_entry(200)])
    finally:
        conn.close()

    result = wantlist_tracklist_cached.run_wantlist_tracklist_cached(200)
    assert result["has_cached_tracklist"] is False
    assert result["track_count"] == 0


def test_wantlist_tracklist_cached_returns_rows(isolated_xdg):
    conn = get_connection()
    try:
        upsert_wantlist_entries(conn, [_wantlist_entry(300)])
        replace_wantlist_tracks(
            conn,
            discogs_release_id=300,
            tracks=[
                {
                    "position": "A1",
                    "title": "Hit",
                    "duration": "3:00",
                    "is_audio_track": True,
                }
            ],
            last_refreshed_at="2026-02-08T00:00:00Z",
        )
    finally:
        conn.close()

    result = wantlist_tracklist_cached.run_wantlist_tracklist_cached(300)
    assert result["has_cached_tracklist"] is True
    assert result["track_count"] == 1
    assert result["audio_track_count"] == 1
    assert result["tracks"][0]["title"] == "Hit"


def test_wantlist_tracklist_show_without_refresh(isolated_xdg):
    conn = get_connection()
    try:
        upsert_wantlist_entries(conn, [_wantlist_entry(400)])
    finally:
        conn.close()

    result = wantlist_tracklist_show.run_wantlist_tracklist_show(400, refresh=False)
    assert result["has_cached_tracklist"] is False
    assert result["track_count"] == 0


def test_wantlist_tracklist_show_with_refresh(isolated_xdg, monkeypatch):
    conn = get_connection()
    try:
        upsert_wantlist_entries(conn, [_wantlist_entry(500)])
    finally:
        conn.close()

    monkeypatch.setenv("DISCOGS_TOKEN", "token")

    class _FakeClient:
        def __init__(self, token: str):
            pass

        def fetch_release_tracklist(self, release_id: int):
            return {
                "tracks": [
                    {
                        "position": "1",
                        "title": "Track One",
                        "duration": "4:00",
                        "is_audio_track": True,
                    }
                ]
            }

    monkeypatch.setattr(wantlist_tracklist_show, "DiscogsClient", _FakeClient)

    result = wantlist_tracklist_show.run_wantlist_tracklist_show(500, refresh=True)

    assert result["has_cached_tracklist"] is True
    assert result["track_count"] == 1
    assert result["tracks"][0]["title"] == "Track One"
