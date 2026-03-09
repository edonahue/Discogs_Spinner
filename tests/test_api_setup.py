"""Tests for GET/POST /api/v1/setup endpoints."""

from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from discogs_player_api.app import create_app
from discogs_player_api.routers import setup as setup_router


def _client() -> TestClient:
    return TestClient(create_app())


def _stub_report(stage: str = "needs_discogs_token", configured: bool = False):
    return {
        "onboarding_stage": stage,
        "discogs": {"configured": configured, "token_source": "missing"},
        "profile": "core",
    }


def test_get_setup_returns_ok_with_onboarding_stage(monkeypatch):
    monkeypatch.setattr(setup_router, "run_setup_report", lambda: _stub_report())
    response = _client().get("/api/v1/setup")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "onboarding_stage" in body["data"]
    assert body["error"] is None
    assert isinstance(body["meta"], dict)


def test_post_setup_saves_token_and_returns_configured(monkeypatch):
    saved = {}

    def fake_config_set(key: str, value: str):
        saved["key"] = key
        saved["value"] = value
        return {"key": key, "value": value}

    monkeypatch.setattr(setup_router, "run_config_set", fake_config_set)
    monkeypatch.setattr(
        setup_router, "run_setup_report", lambda: _stub_report("core_ready", configured=True)
    )

    response = _client().post("/api/v1/setup", json={"discogs_token": "abc123"})
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["discogs"]["configured"] is True
    assert saved == {"key": "discogs_token", "value": "abc123"}
    assert body["error"] is None
    assert isinstance(body["meta"], dict)


def test_post_setup_empty_token_raises_422(monkeypatch):
    response = _client().post("/api/v1/setup", json={"discogs_token": ""})
    assert response.status_code == 422
    body = response.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "request_validation_failed"


def test_post_setup_idempotent(monkeypatch):
    """Calling POST /setup twice with a valid token should succeed both times."""
    call_count = {"n": 0}

    def fake_config_set(key: str, value: str):
        call_count["n"] += 1
        return {"key": key, "value": value}

    monkeypatch.setattr(setup_router, "run_config_set", fake_config_set)
    monkeypatch.setattr(
        setup_router, "run_setup_report", lambda: _stub_report("core_ready", configured=True)
    )

    client = _client()
    r1 = client.post("/api/v1/setup", json={"discogs_token": "tok1"})
    r2 = client.post("/api/v1/setup", json={"discogs_token": "tok1"})
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert call_count["n"] == 2
    for r in (r1, r2):
        body = r.json()
        assert body["error"] is None
        assert isinstance(body["meta"], dict)
