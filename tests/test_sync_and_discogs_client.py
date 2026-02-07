from __future__ import annotations

import pytest

from discogs_player.data.db import get_connection
from discogs_player.data.repo import get_release_counts, upsert_releases
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


class _FakeRequestError(Exception):
    pass


class _FakeHttpxModule:
    RequestError = _FakeRequestError


def test_sync_requires_discogs_token(isolated_xdg, monkeypatch):
    monkeypatch.delenv("DISCOGS_TOKEN", raising=False)

    with pytest.raises(sync_manager.MissingDiscogsTokenError):
        sync_manager.sync_collection()


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
