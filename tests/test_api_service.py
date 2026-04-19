from __future__ import annotations

from types import SimpleNamespace

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from discogs_player_api.app import create_app
from discogs_player_api.routers import catalog, matching, status, sync
from discogs_player_api.routers import value as value_router

# ---------------------------------------------------------------------------
# Recent releases
# ---------------------------------------------------------------------------


def test_api_recent_releases_returns_envelope(monkeypatch):
    stub = {"ok": True, "releases": [], "count": 0, "days": 7, "limit": 25}
    monkeypatch.setattr(catalog, "run_recent_releases", lambda **_: stub)

    client = TestClient(create_app())
    response = client.get("/api/v1/releases/recent")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"] == stub


def test_api_recent_releases_forwards_params(monkeypatch):
    captured: dict[str, object] = {}

    def _fake(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {"ok": True, "releases": [], "count": 0, "days": kwargs.get("days"), "limit": kwargs.get("limit")}

    monkeypatch.setattr(catalog, "run_recent_releases", _fake)

    client = TestClient(create_app())
    client.get("/api/v1/releases/recent?days=14&limit=10")
    assert captured["days"] == 14
    assert captured["limit"] == 10


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------


def test_api_analytics_returns_envelope(monkeypatch):
    stub = {
        "release_count_active": 50,
        "mapped_count": 40,
        "unmatched_count": 10,
        "top_limit": 10,
        "by_release_year": [],
        "acquisition_timeline": [],
        "top_genres": [],
        "top_styles": [],
        "top_artists": [],
    }
    monkeypatch.setattr(status, "run_collection_analytics", lambda **_: stub)

    client = TestClient(create_app())
    response = client.get("/api/v1/analytics")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"] == stub


# ---------------------------------------------------------------------------
# Tracklist
# ---------------------------------------------------------------------------


def test_api_tracklist_happy_path(monkeypatch):
    stub = {
        "discogs_release_id": 42,
        "title": "OK Computer",
        "artist": "Radiohead",
        "has_cached_tracklist": True,
        "has_tracklist": True,
        "tracks": [{"position": "1", "title": "Airbag", "duration": "4:44", "type_": "track"}],
        "track_count": 1,
        "audio_track_count": 1,
        "tracklist_last_refreshed_at": "2026-01-01T00:00:00Z",
    }
    monkeypatch.setattr(catalog, "run_release_tracklist_show", lambda rid, **_: stub)

    client = TestClient(create_app())
    response = client.get("/api/v1/releases/42/tracklist")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["has_cached_tracklist"] is True
    assert len(body["data"]["tracks"]) == 1


def test_api_tracklist_not_found_returns_400(monkeypatch):
    def _raise(rid: int, **_: object) -> dict[str, object]:
        _ = rid
        raise ValueError("Release not found: 999")

    monkeypatch.setattr(catalog, "run_release_tracklist_show", _raise)

    client = TestClient(create_app())
    response = client.get("/api/v1/releases/999/tracklist")
    assert response.status_code == 400
    body = response.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "invalid_request"


def test_api_status_uses_envelope(monkeypatch):
    payload = {
        "release_count_total": 10,
        "release_count_active": 9,
        "mapped_count": 8,
        "unmatched_count": 1,
    }
    monkeypatch.setattr(status, "get_status_report", lambda: payload)

    client = TestClient(create_app())
    response = client.get("/api/v1/status")
    assert response.status_code == 200
    body = response.json()

    assert body["ok"] is True
    assert body["data"] == payload
    assert body["error"] is None
    assert isinstance(body["meta"], dict)


def test_api_capabilities_uses_capability_model(monkeypatch):
    spotify = SimpleNamespace(
        addon_available=True,
        configured=False,
        action_label="Connect Spotify",
        status_message="Needs auth",
    )
    monkeypatch.setattr(
        status,
        "get_capabilities",
        lambda: SimpleNamespace(spotify=spotify),
    )

    client = TestClient(create_app())
    response = client.get("/api/v1/capabilities")
    assert response.status_code == 200
    body = response.json()

    assert body["ok"] is True
    assert body["data"]["spotify"]["addon_available"] is True
    assert body["data"]["spotify"]["configured"] is False
    assert body["data"]["spotify"]["action_label"] == "Connect Spotify"


def test_api_capabilities_includes_provider_listing_when_available(monkeypatch):
    spotify = SimpleNamespace(
        addon_available=True,
        configured=True,
        action_label="Spotify Ready",
        status_message="Spotify playback and matching are available.",
    )
    provider = SimpleNamespace(
        provider_id="youtube_music",
        display_name="YouTube Music",
        listed=True,
        enabled=False,
        importable=False,
        addon_available=False,
        configured=False,
        action_label="Planned",
        status_message="Provider listed but disabled.",
        docs_url="https://music.youtube.com/",
        experimental=True,
        experimental_flag="DP_ENABLE_EXPERIMENTAL_YOUTUBE_MUSIC",
    )
    monkeypatch.setattr(
        status,
        "get_capabilities",
        lambda: SimpleNamespace(spotify=spotify, providers=(provider,)),
    )

    client = TestClient(create_app())
    response = client.get("/api/v1/capabilities")
    assert response.status_code == 200
    body = response.json()

    assert body["ok"] is True
    providers = body["data"]["providers"]
    assert isinstance(providers, list)
    assert providers[0]["provider_id"] == "youtube_music"
    assert providers[0]["action_label"] == "Planned"


def test_api_sync_collection_forwards_allow_empty_deactivate(monkeypatch):
    captured: dict[str, object] = {}

    def _fake_run_sync_collection(*, allow_empty_deactivate: bool, progress_callback=None):
        _ = progress_callback
        captured["allow_empty_deactivate"] = allow_empty_deactivate
        return {"ok": True, "synced": 5}

    monkeypatch.setattr(sync, "run_sync_collection", _fake_run_sync_collection)

    client = TestClient(create_app())
    response = client.post(
        "/api/v1/sync/collection",
        json={"allow_empty_deactivate": True},
    )
    assert response.status_code == 200
    assert captured["allow_empty_deactivate"] is True
    assert response.json()["ok"] is True
    assert response.json()["data"]["synced"] == 5


def test_api_sync_wantlist_forwards_allow_empty_deactivate(monkeypatch):
    captured: dict[str, object] = {}

    def _fake_run_sync_wantlist(*, allow_empty_deactivate: bool, progress_callback=None):
        _ = progress_callback
        captured["allow_empty_deactivate"] = allow_empty_deactivate
        return {"ok": True, "synced": 2}

    monkeypatch.setattr(sync, "run_sync_wantlist", _fake_run_sync_wantlist)

    client = TestClient(create_app())
    response = client.post(
        "/api/v1/sync/wantlist",
        json={"allow_empty_deactivate": True},
    )
    assert response.status_code == 200
    assert captured["allow_empty_deactivate"] is True
    assert response.json()["ok"] is True
    assert response.json()["data"]["synced"] == 2


def test_api_list_releases_forwards_filter_params(monkeypatch):
    captured: dict[str, object] = {}

    def _fake_run_list_releases(**kwargs):
        captured.update(kwargs)
        return [{"discogs_release_id": 1, "artist": "A", "title": "B"}]

    monkeypatch.setattr(catalog, "run_list_releases", _fake_run_list_releases)

    client = TestClient(create_app())
    response = client.get(
        "/api/v1/releases",
        params=[
            ("q", "beck"),
            ("genres", "Rock"),
            ("genres", "Pop"),
            ("styles", "Indie"),
            ("year", "2017"),
            ("limit", "33"),
            ("unmatched", "true"),
            ("with_value", "true"),
        ],
    )

    assert response.status_code == 200
    assert captured["q"] == "beck"
    assert captured["genres"] == ["Rock", "Pop"]
    assert captured["styles"] == ["Indie"]
    assert captured["year"] == "2017"
    assert captured["limit"] == 33
    assert captured["unmatched"] is True
    assert captured["with_value"] is True


def test_api_maps_use_case_value_error_to_consistent_envelope(monkeypatch):
    def _fake_run_match_review_action(*args, **kwargs):
        _ = (args, kwargs)
        raise ValueError("bad review request")

    monkeypatch.setattr(
        matching,
        "run_match_audit_review_action",
        _fake_run_match_review_action,
    )

    client = TestClient(create_app())
    response = client.post("/api/v1/match/review/apply", json={})
    assert response.status_code == 400

    body = response.json()
    assert body["ok"] is False
    assert body["data"] is None
    assert body["error"]["code"] == "invalid_request"
    assert "bad review request" in body["error"]["message"]
    assert body["error"]["retryable"] is False


def test_api_value_queue_returns_envelope(monkeypatch):
    stub = {
        "total_candidates": 3,
        "missing_count": 1,
        "unpriced_count": 1,
        "stale_count": 1,
        "stale_days": 30,
        "limit": 25,
        "queue": [],
    }
    monkeypatch.setattr(value_router, "run_value_refresh_queue", lambda **_: stub)

    client = TestClient(create_app())
    response = client.get("/api/v1/value/queue")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"] == stub


def test_api_collection_health_returns_envelope(monkeypatch):
    stub = {
        "score": 82,
        "total_active": 200,
        "buckets": [],
    }
    monkeypatch.setattr(value_router, "run_collection_health", lambda: stub)

    client = TestClient(create_app())
    response = client.get("/api/v1/value/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"] == stub


def test_api_validation_errors_use_standard_error_envelope():
    client = TestClient(create_app())
    response = client.post(
        "/api/v1/sync/collection",
        json={"allow_empty_deactivate": {"invalid": "value"}},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "request_validation_failed"
    assert isinstance(body["error"]["details"], dict)
