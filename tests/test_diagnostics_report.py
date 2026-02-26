from __future__ import annotations

import json
from types import SimpleNamespace

from discogs_player.use_cases import diagnostics_report


def test_run_diagnostics_report_redacts_settings_and_exposes_presence(monkeypatch):
    class _FakeBackend:
        name = "spotify"

        def auth_diagnostics(self):
            return {"diagnosis": "ok", "configured": True}

    monkeypatch.setattr(
        diagnostics_report,
        "get_capabilities",
        lambda: SimpleNamespace(
            spotify=SimpleNamespace(
                addon_available=True,
                configured=True,
                action_label="Spotify Ready",
                status_message="Spotify playback and matching are available.",
            )
        ),
    )
    monkeypatch.setattr(diagnostics_report, "get_player_backend", lambda: _FakeBackend())
    monkeypatch.setattr(
        diagnostics_report,
        "list_settings",
        lambda: {"discogs_token": "super-secret", "theme": "nano"},
    )
    monkeypatch.setattr(
        diagnostics_report,
        "get_status_report",
        lambda: {"release_count_total": 1},
    )
    monkeypatch.setattr(
        diagnostics_report,
        "run_setup_report",
        lambda: {"onboarding_stage": "ready"},
    )
    monkeypatch.setenv("DISCOGS_TOKEN", "env-secret")

    payload = diagnostics_report.run_diagnostics_report()
    serialized = json.dumps(payload)

    assert payload["settings_presence"]["discogs_token"]["present"] is True
    assert payload["settings_presence"]["discogs_token"]["redacted"] is True
    assert payload["settings_presence"]["theme"]["present"] is True
    assert payload["env_presence"]["DISCOGS_TOKEN"] is True
    assert payload["provider_diagnostics"]["spotify"]["diagnosis"] == "ok"
    assert "super-secret" not in serialized
    assert "env-secret" not in serialized


def test_run_diagnostics_report_handles_provider_diagnostics_error(monkeypatch):
    class _FailingBackend:
        name = "spotify"

        def auth_diagnostics(self):
            raise RuntimeError("diagnostic probe failed")

    monkeypatch.setattr(
        diagnostics_report,
        "get_capabilities",
        lambda: SimpleNamespace(
            spotify=SimpleNamespace(
                addon_available=False,
                configured=False,
                action_label="Enable Spotify (optional)",
                status_message="Spotify addon missing.",
            )
        ),
    )
    monkeypatch.setattr(
        diagnostics_report, "get_player_backend", lambda: _FailingBackend()
    )
    monkeypatch.setattr(diagnostics_report, "list_settings", lambda: {})
    monkeypatch.setattr(
        diagnostics_report,
        "get_status_report",
        lambda: {"release_count_total": 0},
    )
    monkeypatch.setattr(
        diagnostics_report,
        "run_setup_report",
        lambda: {"onboarding_stage": "needs_discogs_token"},
    )

    payload = diagnostics_report.run_diagnostics_report()
    provider_payload = payload["provider_diagnostics"]["spotify"]

    assert provider_payload["diagnosis"] == "error"
    assert "diagnostic probe failed" in str(provider_payload["status_message"])
