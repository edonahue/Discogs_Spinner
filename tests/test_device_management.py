from __future__ import annotations

import pytest

from discogs_player.core.settings import get_setting
from discogs_player.data.db import get_connection
from discogs_player.use_cases import device_management


class _FakeBackend:
    devices: list[dict[str, object]] = []

    @classmethod
    def addon_available(cls) -> bool:
        return True

    def is_configured(self, *, conn=None) -> bool:
        _ = conn
        return True

    def list_devices(self, *, conn=None) -> list[dict[str, object]]:
        _ = conn
        return [dict(item) for item in self.devices]


def test_choose_auto_device_prefers_active_computer():
    devices = [
        {
            "id": "speaker-1",
            "name": "Kitchen",
            "type": "Speaker",
            "is_active": False,
            "is_restricted": False,
        },
        {
            "id": "pc-1",
            "name": "X600 Desktop",
            "type": "Computer",
            "is_active": True,
            "is_restricted": False,
        },
    ]

    selected = device_management.choose_auto_device(devices)
    assert selected["id"] == "pc-1"


def test_choose_auto_device_requires_devices():
    with pytest.raises(device_management.NoSpotifyDevicesError):
        device_management.choose_auto_device([])


def test_run_list_devices_marks_default(isolated_xdg, monkeypatch):
    _FakeBackend.devices = [
        {
            "id": "dev-1",
            "name": "Desk",
            "type": "Computer",
            "is_active": True,
            "is_restricted": False,
            "volume_percent": 50,
        },
        {
            "id": "dev-2",
            "name": "Phone",
            "type": "Smartphone",
            "is_active": False,
            "is_restricted": False,
            "volume_percent": 100,
        },
    ]

    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO app_settings(key, value) VALUES (?, ?)",
            ("default_spotify_device_id", "dev-2"),
        )
        conn.commit()
    finally:
        conn.close()

    monkeypatch.setattr(
        device_management, "get_player_backend", lambda: _FakeBackend()
    )

    devices = device_management.run_list_devices()
    assert len(devices) == 2
    assert [device["is_default"] for device in devices] == [False, True]


def test_run_set_default_device_persists_selection(isolated_xdg, monkeypatch):
    _FakeBackend.devices = [
        {
            "id": "dev-1",
            "name": "Desk",
            "type": "Computer",
            "is_active": True,
            "is_restricted": False,
            "volume_percent": 50,
        }
    ]

    monkeypatch.setattr(
        device_management, "get_player_backend", lambda: _FakeBackend()
    )

    selected = device_management.run_set_default_device("dev-1")
    assert selected == {"id": "dev-1", "name": "Desk"}

    conn = get_connection()
    try:
        assert get_setting("default_spotify_device_id", conn=conn) == "dev-1"
        assert get_setting("default_spotify_device_name", conn=conn) == "Desk"
    finally:
        conn.close()


def test_run_auto_set_default_device_persists_selection(isolated_xdg, monkeypatch):
    _FakeBackend.devices = [
        {
            "id": "dev-1",
            "name": "Living Room",
            "type": "Speaker",
            "is_active": False,
            "is_restricted": False,
            "volume_percent": 20,
        },
        {
            "id": "dev-2",
            "name": "Linux Desktop",
            "type": "Computer",
            "is_active": True,
            "is_restricted": False,
            "volume_percent": 80,
        },
    ]

    monkeypatch.setattr(
        device_management, "get_player_backend", lambda: _FakeBackend()
    )

    selected = device_management.run_auto_set_default_device()
    assert selected == {"id": "dev-2", "name": "Linux Desktop"}

    conn = get_connection()
    try:
        assert get_setting("default_spotify_device_id", conn=conn) == "dev-2"
        assert get_setting("default_spotify_device_name", conn=conn) == "Linux Desktop"
    finally:
        conn.close()
