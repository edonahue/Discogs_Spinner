from __future__ import annotations

import pytest

from discogs_player.core.settings import set_setting
from discogs_player.data.db import get_connection
from discogs_player.data.repo import (
    get_release_counts,
    get_wantlist_count,
    upsert_releases,
    upsert_wantlist_entries,
)
from discogs_player.services import sync_manager
from discogs_player.services.discogs_client import DiscogsApiError, DiscogsClient
import discogs_player.services.discogs_client as discogs_client


def _release(release_id: int):
    return {
        "discogs_release_id": release_id,
        "artist": "Artist",
        "title": "Title",
        "year": 2000,
        "genres": ["Rock"],
        "styles": ["Alt"],
        "thumb_url": None,
        "cover_url": None,
        "added_at": "2026-01-01T00:00:00Z",
        "last_synced_at": "2026-01-01T00:00:00Z",
        "is_active": 1,
    }


class _FakeClientEmpty:
    def __init__(self, token: str):
        self.token = token

    def fetch_collection_releases(self, **kwargs):
        _ = kwargs
        return []


class _FakeWantlistClientEmpty:
    def __init__(self, token: str):
        self.token = token

    def fetch_wantlist_releases(self, **kwargs):
        _ = kwargs
        return []


class _FakeRequestError(Exception):
    pass


class _FakeHttpxModule:
    RequestError = _FakeRequestError


def test_sync_requires_discogs_token(isolated_xdg, monkeypatch):
    monkeypatch.delenv("DISCOGS_TOKEN", raising=False)

    with pytest.raises(sync_manager.MissingDiscogsTokenError):
        sync_manager.sync_collection()


def test_sync_uses_discogs_token_from_settings_when_env_missing(
    isolated_xdg, monkeypatch
):
    monkeypatch.delenv("DISCOGS_TOKEN", raising=False)
    conn = get_connection()
    try:
        set_setting("discogs_token", "stored-token", conn=conn)
    finally:
        conn.close()

    seen: dict[str, str] = {}

    class _FakeClientFromSettings:
        def __init__(self, token: str):
            seen["token"] = token

        def fetch_collection_releases(self, **kwargs):
            _ = kwargs
            return []

    monkeypatch.setattr(sync_manager, "DiscogsClient", _FakeClientFromSettings)
    summary = sync_manager.sync_collection()

    assert seen["token"] == "stored-token"
    assert summary["fetched_count"] == 0


def test_sync_skips_empty_deactivate_by_default(isolated_xdg, monkeypatch):
    conn = get_connection()
    try:
        upsert_releases(conn, [_release(1)])
    finally:
        conn.close()

    monkeypatch.setenv("DISCOGS_TOKEN", "token")
    monkeypatch.setattr(sync_manager, "DiscogsClient", _FakeClientEmpty)

    summary = sync_manager.sync_collection(allow_empty_deactivate=False)

    conn = get_connection()
    try:
        counts = get_release_counts(conn)
    finally:
        conn.close()

    assert summary["fetched_count"] == 0
    assert summary["deactivated_count"] == 0
    assert summary["skipped_empty_deactivate"] is True
    assert summary["warnings"]
    assert counts["release_count_active"] == 1


def test_sync_full_allows_empty_deactivate(isolated_xdg, monkeypatch):
    conn = get_connection()
    try:
        upsert_releases(conn, [_release(1)])
    finally:
        conn.close()

    monkeypatch.setenv("DISCOGS_TOKEN", "token")
    monkeypatch.setattr(sync_manager, "DiscogsClient", _FakeClientEmpty)

    summary = sync_manager.sync_collection(allow_empty_deactivate=True)

    conn = get_connection()
    try:
        counts = get_release_counts(conn)
    finally:
        conn.close()

    assert summary["deactivated_count"] == 1
    assert summary["skipped_empty_deactivate"] is False
    assert summary["warnings"] == []
    assert counts["release_count_active"] == 0


def test_wantlist_sync_skips_empty_deactivate_by_default(isolated_xdg, monkeypatch):
    conn = get_connection()
    try:
        upsert_wantlist_entries(
            conn,
            [
                {
                    "discogs_release_id": 901,
                    "artist": "Artist",
                    "title": "Title",
                    "year": 2001,
                    "genres": ["Rock"],
                    "styles": ["Alt"],
                    "thumb_url": None,
                    "cover_url": None,
                    "notes": None,
                    "added_at": "2026-01-01T00:00:00Z",
                    "last_synced_at": "2026-01-01T00:00:00Z",
                    "is_active": 1,
                }
            ],
        )
    finally:
        conn.close()

    monkeypatch.setenv("DISCOGS_TOKEN", "token")
    monkeypatch.setattr(sync_manager, "DiscogsClient", _FakeWantlistClientEmpty)

    summary = sync_manager.sync_wantlist(allow_empty_deactivate=False)

    conn = get_connection()
    try:
        active_count = get_wantlist_count(conn)
    finally:
        conn.close()

    assert summary["fetched_count"] == 0
    assert summary["deactivated_count"] == 0
    assert summary["skipped_empty_deactivate"] is True
    assert summary["warnings"]
    assert active_count == 1


def test_wantlist_sync_full_allows_empty_deactivate(isolated_xdg, monkeypatch):
    conn = get_connection()
    try:
        upsert_wantlist_entries(
            conn,
            [
                {
                    "discogs_release_id": 902,
                    "artist": "Artist",
                    "title": "Title",
                    "year": 2001,
                    "genres": ["Rock"],
                    "styles": ["Alt"],
                    "thumb_url": None,
                    "cover_url": None,
                    "notes": None,
                    "added_at": "2026-01-01T00:00:00Z",
                    "last_synced_at": "2026-01-01T00:00:00Z",
                    "is_active": 1,
                }
            ],
        )
    finally:
        conn.close()

    monkeypatch.setenv("DISCOGS_TOKEN", "token")
    monkeypatch.setattr(sync_manager, "DiscogsClient", _FakeWantlistClientEmpty)

    summary = sync_manager.sync_wantlist(allow_empty_deactivate=True)

    conn = get_connection()
    try:
        active_count = get_wantlist_count(conn)
    finally:
        conn.close()

    assert summary["deactivated_count"] == 1
    assert summary["skipped_empty_deactivate"] is False
    assert summary["warnings"] == []
    assert active_count == 0


def test_discogs_request_wraps_transport_errors(monkeypatch):
    client = DiscogsClient(token="token")

    class _FailingClient:
        def __init__(self):
            self.calls = 0

        def request(self, method, url, params=None):
            _ = (method, url, params)
            self.calls += 1
            raise _FakeRequestError("network down")

    failing_client = _FailingClient()
    monkeypatch.setattr(discogs_client.time, "sleep", lambda *_: None)

    with pytest.raises(DiscogsApiError, match="transport error"):
        client._request_with_backoff(
            failing_client,
            "GET",
            "/users/me",
            httpx_module=_FakeHttpxModule,
        )

    assert failing_client.calls == 5


def test_discogs_identity_invalid_json():
    client = DiscogsClient(token="token")

    class _Response:
        status_code = 200
        headers = {}
        text = "not-json"

        def json(self):
            raise ValueError("bad json")

    class _Client:
        def request(self, method, url, params=None):
            _ = (method, url, params)
            return _Response()

    with pytest.raises(DiscogsApiError, match="not valid JSON"):
        client._get_username(_Client(), httpx_module=_FakeHttpxModule)


def test_normalize_release_year_string():
    client = DiscogsClient(token="token")
    normalized = client._normalize_release(
        {
            "date_added": "2026-02-07T00:00:00+00:00",
            "basic_information": {
                "id": 123,
                "title": "Album",
                "year": "1999",
                "artists": [{"name": "Artist"}],
                "genres": ["Rock"],
                "styles": ["Indie"],
                "thumb": "",
                "cover_image": "",
            },
        },
        "2026-02-07T00:00:00+00:00",
    )

    assert normalized is not None
    assert normalized["year"] == 1999


def test_normalize_wantlist_release_includes_notes():
    client = DiscogsClient(token="token")
    normalized = client._normalize_wantlist_release(
        {
            "date_added": "2026-02-07T00:00:00+00:00",
            "notes": "Need this pressing",
            "basic_information": {
                "id": 555,
                "title": "Album",
                "year": "1980",
                "artists": [{"name": "Artist"}],
                "genres": ["Rock"],
                "styles": ["Post-Punk"],
                "thumb": "",
                "cover_image": "",
            },
        },
        "2026-02-07T00:00:00+00:00",
    )

    assert normalized is not None
    assert normalized["discogs_release_id"] == 555
    assert normalized["year"] == 1980
    assert normalized["notes"] == "Need this pressing"


def test_extract_market_price_suggestions():
    client = DiscogsClient(token="token")
    stats = client._extract_market_price_suggestions(
        {
            "Mint (M)": {"currency": "USD", "value": 25.0},
            "Very Good Plus (VG+)": {"currency": "USD", "value": 15.0},
            "Good (G)": {"currency": "USD", "value": 5.0},
        }
    )

    assert stats["lowest"] == 5.0
    assert stats["median"] == 15.0
    assert stats["highest"] == 25.0
    assert stats["currency"] == "USD"


def test_extract_release_tracklist_rows():
    client = DiscogsClient(token="token")
    rows = client._extract_release_tracklist(
        {
            "id": 123,
            "tracklist": [
                {
                    "position": "A1",
                    "title": "Opening",
                    "duration": "4:05",
                    "type_": "track",
                },
                {
                    "position": "",
                    "title": "Side A",
                    "duration": "",
                    "type_": "heading",
                },
            ],
        }
    )

    assert rows == [
        {
            "position": "A1",
            "title": "Opening",
            "duration": "4:05",
            "type": "track",
            "is_audio_track": True,
        },
        {
            "position": None,
            "title": "Side A",
            "duration": None,
            "type": "heading",
            "is_audio_track": False,
        },
    ]


def test_extract_release_tracklist_rejects_invalid_shape():
    client = DiscogsClient(token="token")
    with pytest.raises(DiscogsApiError, match="tracklist had unexpected format"):
        client._extract_release_tracklist({"tracklist": {"position": "A1"}})
