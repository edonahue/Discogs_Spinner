"""Unit tests for YouTubeMusicClient search."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from discogs_player.integrations.player_backend import PlayerApiError
from discogs_player.integrations.youtube_music.ytmusic_client import (
    YouTubeMusicClient,
    _normalise_result,
)


def test_normalise_result_full():
    raw = {
        "browseId": "MPREb_abc123",
        "title": "OK Computer",
        "artists": [{"name": "Radiohead", "id": "some-id"}],
        "year": 1997,
        "trackCount": 12,
    }
    result = _normalise_result(raw)
    assert result["id"] == "MPREb_abc123"
    assert result["name"] == "OK Computer"
    assert result["artists"] == [{"name": "Radiohead"}]
    assert result["release_date"] == 1997
    assert result["total_tracks"] == 12


def test_normalise_result_missing_fields():
    result = _normalise_result({})
    assert result["id"] == ""
    assert result["name"] == ""
    assert result["artists"] == []
    assert result["release_date"] is None
    assert result["total_tracks"] == 0


def test_normalise_result_year_as_string():
    result = _normalise_result({"year": "2001"})
    assert result["release_date"] == 2001


def test_search_albums_returns_normalised_list(monkeypatch):
    fake_ytmusic = MagicMock()
    fake_ytmusic.return_value.search.return_value = [
        {
            "browseId": "MPREb_x",
            "title": "Kid A",
            "artists": [{"name": "Radiohead"}],
            "year": 2000,
            "trackCount": 10,
        }
    ]
    monkeypatch.setitem(__import__("sys").modules, "ytmusicapi", MagicMock(YTMusic=fake_ytmusic))

    client = YouTubeMusicClient()
    results = client.search_albums("Radiohead Kid A", limit=5)
    assert len(results) == 1
    assert results[0]["id"] == "MPREb_x"
    assert results[0]["name"] == "Kid A"


def test_search_albums_returns_empty_on_non_list_response(monkeypatch):
    fake_ytmusic = MagicMock()
    fake_ytmusic.return_value.search.return_value = None
    monkeypatch.setitem(__import__("sys").modules, "ytmusicapi", MagicMock(YTMusic=fake_ytmusic))

    client = YouTubeMusicClient()
    results = client.search_albums("anything")
    assert results == []


def test_search_albums_raises_player_api_error_on_exception(monkeypatch):
    fake_ytmusic = MagicMock()
    fake_ytmusic.return_value.search.side_effect = RuntimeError("network failure")
    monkeypatch.setitem(__import__("sys").modules, "ytmusicapi", MagicMock(YTMusic=fake_ytmusic))

    client = YouTubeMusicClient()
    with pytest.raises(PlayerApiError, match="network failure"):
        client.search_albums("anything")


def test_search_albums_raises_player_api_error_when_ytmusicapi_missing(monkeypatch):
    import sys

    saved = sys.modules.pop("ytmusicapi", None)
    try:
        monkeypatch.delitem(sys.modules, "ytmusicapi", raising=False)

        def _fake_import(name, *args, **kwargs):
            if name == "ytmusicapi":
                raise ImportError("No module named 'ytmusicapi'")
            return original_import(name, *args, **kwargs)

        import builtins

        original_import = builtins.__import__
        monkeypatch.setattr(builtins, "__import__", _fake_import)

        client = YouTubeMusicClient()
        with pytest.raises(PlayerApiError, match="ytmusicapi"):
            client.search_albums("anything")
    finally:
        if saved is not None:
            sys.modules["ytmusicapi"] = saved
