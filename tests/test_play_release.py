from __future__ import annotations

import pytest

from discogs_player.core.settings import get_setting, set_setting
from discogs_player.data.db import get_connection
from discogs_player.data.repo import upsert_releases
from discogs_player.use_cases import play_release


class _FakeSpotifyClient:
    devices: list[dict[str, object]] = []
    playback_calls: list[tuple[str, str | None]] = []

    def __init__(self, access_token: str):
        self.access_token = access_token

    def list_devices(self) -> list[dict[str, object]]:
        return [dict(item) for item in self.devices]

    def start_album_playback(self, spotify_album_id: str, *, device_id: str | None = None) -> None:
        self.playback_calls.append((spotify_album_id, device_id))


def _release(release_id: int) -> dict[str, object]:
    return {
        "discogs_release_id": release_id,
        "artist": "Artist",
        "title": "Album",
        "year": 2001,
        "genres": ["Rock"],
        "styles": ["Alt"],
        "thumb_url": None,
        "cover_url": None,
        "added_at": "2026-01-01T00:00:00Z",
        "last_synced_at": "2026-01-01T00:00:00Z",
        "is_active": 1,
    }


def _seed_mapping(conn, discogs_release_id: int, spotify_album_id: str) -> None:
    conn.execute(
        """
        INSERT INTO spotify_mapping(discogs_release_id, spotify_album_id, confidence, last_checked_at, is_override)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(discogs_release_id) DO UPDATE SET spotify_album_id = excluded.spotify_album_id
        """,
        (discogs_release_id, spotify_album_id, 0.95, "2026-01-01T00:00:00Z", 0),
    )
    conn.commit()


def test_play_release_uses_last_spin_and_auto_device(isolated_xdg, monkeypatch):
    _FakeSpotifyClient.playback_calls = []
    _FakeSpotifyClient.devices = [
        {
            "id": "speaker-1",
            "name": "Kitchen",
            "type": "Speaker",
            "is_active": False,
            "is_restricted": False,
            "volume_percent": 25,
        },
        {
            "id": "desk-1",
            "name": "X600 Desktop",
            "type": "Computer",
            "is_active": True,
            "is_restricted": False,
            "volume_percent": 70,
        },
    ]

    conn = get_connection()
    try:
        upsert_releases(conn, [_release(111)])
        _seed_mapping(conn, 111, "spotify:album:abc123")
        set_setting("last_spin_release_id", "111", conn=conn)
    finally:
        conn.close()

    monkeypatch.setattr(play_release, "SpotifyClient", _FakeSpotifyClient)
    monkeypatch.setattr(play_release, "get_spotify_access_token", lambda conn=None: "token")

    result = play_release.run_play_release(use_last_spin=True)

    assert result["discogs_release_id"] == 111
    assert result["device_id"] == "desk-1"
    assert _FakeSpotifyClient.playback_calls == [("spotify:album:abc123", "desk-1")]

    conn = get_connection()
    try:
        assert get_setting("default_spotify_device_id", conn=conn) == "desk-1"
    finally:
        conn.close()


def test_play_release_uses_existing_default_device(isolated_xdg, monkeypatch):
    _FakeSpotifyClient.playback_calls = []
    _FakeSpotifyClient.devices = [
        {
            "id": "phone-1",
            "name": "Phone",
            "type": "Smartphone",
            "is_active": False,
            "is_restricted": False,
            "volume_percent": 20,
        },
        {
            "id": "desk-1",
            "name": "Desk",
            "type": "Computer",
            "is_active": True,
            "is_restricted": False,
            "volume_percent": 80,
        },
    ]

    conn = get_connection()
    try:
        upsert_releases(conn, [_release(222)])
        _seed_mapping(conn, 222, "album-222")
        set_setting("default_spotify_device_id", "phone-1", conn=conn)
        set_setting("default_spotify_device_name", "Phone", conn=conn)
    finally:
        conn.close()

    monkeypatch.setattr(play_release, "SpotifyClient", _FakeSpotifyClient)
    monkeypatch.setattr(play_release, "get_spotify_access_token", lambda conn=None: "token")

    result = play_release.run_play_release(discogs_release_id=222)
    assert result["device_id"] == "phone-1"
    assert _FakeSpotifyClient.playback_calls == [("album-222", "phone-1")]


def test_play_release_requires_last_spin_value(isolated_xdg):
    with pytest.raises(play_release.MissingLastSpinError):
        play_release.run_play_release(use_last_spin=True)


def test_play_release_requires_mapping(isolated_xdg):
    conn = get_connection()
    try:
        upsert_releases(conn, [_release(333)])
    finally:
        conn.close()

    with pytest.raises(play_release.MissingSpotifyMappingError):
        play_release.run_play_release(discogs_release_id=333)


def test_play_release_requires_single_selector(isolated_xdg):
    with pytest.raises(ValueError):
        play_release.run_play_release(discogs_release_id=1, use_last_spin=True)


def test_play_release_fails_when_no_devices(isolated_xdg, monkeypatch):
    _FakeSpotifyClient.playback_calls = []
    _FakeSpotifyClient.devices = []

    conn = get_connection()
    try:
        upsert_releases(conn, [_release(444)])
        _seed_mapping(conn, 444, "spotify:album:444")
    finally:
        conn.close()

    monkeypatch.setattr(play_release, "SpotifyClient", _FakeSpotifyClient)
    monkeypatch.setattr(play_release, "get_spotify_access_token", lambda conn=None: "token")

    with pytest.raises(play_release.NoPlayableDeviceError):
        play_release.run_play_release(discogs_release_id=444)
