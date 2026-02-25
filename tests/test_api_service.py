from __future__ import annotations

from types import SimpleNamespace

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from discogs_player_api.app import create_app
from discogs_player_api.routers import catalog, matching, status, sync


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

