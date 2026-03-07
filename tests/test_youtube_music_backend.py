"""Unit tests for YouTubeMusicPlayerBackend."""

from __future__ import annotations

import importlib.util
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import discogs_player.integrations.youtube_music.backend as yt_backend_module
from discogs_player.integrations.youtube_music.backend import (
    YouTubeMusicPlayerBackend,
    _YTM_BROWSE_BASE,
)


def test_name():
    backend = YouTubeMusicPlayerBackend()
    assert backend.name == "youtube_music"


def test_is_configured_always_true():
    backend = YouTubeMusicPlayerBackend()
    assert backend.is_configured() is True


def test_list_devices_returns_single_browser_entry():
    backend = YouTubeMusicPlayerBackend()
    devices = backend.list_devices()
    assert len(devices) == 1
    device = devices[0]
    assert device["id"] == "browser"
    assert "YouTube Music" in str(device["name"])
    assert device["is_active"] is True


def test_addon_available_when_ytmusicapi_importable(monkeypatch):
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: object())
    assert YouTubeMusicPlayerBackend.addon_available() is True


def test_addon_not_available_when_ytmusicapi_missing(monkeypatch):
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
    assert YouTubeMusicPlayerBackend.addon_available() is False


def test_start_album_playback_opens_correct_url(monkeypatch):
    opened_urls: list[str] = []
    monkeypatch.setattr(yt_backend_module.webbrowser, "open", opened_urls.append)
    backend = YouTubeMusicPlayerBackend()
    backend.start_album_playback("MPREb_someAlbumId")
    assert opened_urls == [f"{_YTM_BROWSE_BASE}MPREb_someAlbumId"]


def test_start_album_playback_ignores_device_id(monkeypatch):
    opened_urls: list[str] = []
    monkeypatch.setattr(yt_backend_module.webbrowser, "open", opened_urls.append)
    backend = YouTubeMusicPlayerBackend()
    backend.start_album_playback("MPREb_xyz", device_id="browser")
    assert len(opened_urls) == 1


def test_run_oauth_login_returns_ok_dict():
    backend = YouTubeMusicPlayerBackend()
    result = backend.run_oauth_login()
    assert result.get("ok") is True
    assert "message" in result


def test_create_matching_client_returns_ytmusic_client():
    from discogs_player.integrations.youtube_music.ytmusic_client import YouTubeMusicClient

    backend = YouTubeMusicPlayerBackend()
    client = backend.create_matching_client()
    assert isinstance(client, YouTubeMusicClient)


def test_auth_diagnostics_includes_backend_key():
    backend = YouTubeMusicPlayerBackend()
    diag = backend.auth_diagnostics()
    assert diag.get("backend") == "youtube_music"
    assert diag.get("configured") is True
    assert "addon_available" in diag
