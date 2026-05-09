from __future__ import annotations

from discogs_player.capabilities import AppCapabilities, SpotifyCapabilities
from discogs_player.core.settings import set_setting
from discogs_player.data.db import get_connection
from discogs_player.data.repo import upsert_releases
from discogs_player.use_cases import setup_report
from discogs_player.use_cases.setup_report import _discogs_token_source


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


def test_setup_report_requires_discogs_token_and_spotify_addon(
    isolated_xdg, monkeypatch
):
    monkeypatch.delenv("DISCOGS_TOKEN", raising=False)
    monkeypatch.setattr(
        setup_report,
        "get_capabilities",
        lambda: AppCapabilities(
            spotify=SpotifyCapabilities(
                addon_available=False,
                configured=False,
                action_label="Enable Spotify (optional)",
                status_message="Spotify addon missing.",
            )
        ),
    )

    conn = get_connection()
    try:
        upsert_releases(conn, [_release(222)])
    finally:
        conn.close()

    report = setup_report.run_setup_report()

    assert report["profile"] == "core"
    assert report["onboarding_stage"] == "needs_discogs_token"
    assert report["discogs"]["configured"] is False
    assert report["spotify"]["addon_available"] is False
    readiness = report["provider_readiness"]
    assert readiness["core_service"]["service_id"] == "discogs"
    assert readiness["core_service"]["required"] is True
    assert readiness["summary"]["required_services_configured"] is False
    checklist = report["first_run_checklist"]
    assert checklist["discogs_configured"] is False
    assert checklist["collection_synced"] is True
    assert checklist["ready_for_daily_use"] is False
    assert (
        report["discogs"]["token_setup_url"]
        == "https://www.discogs.com/settings/developers"
    )
    assert (
        report["links"]["spotify_dashboard_url"]
        == "https://developer.spotify.com/dashboard"
    )
    assert isinstance(report["daily_use_actions"], list)
    assert report["daily_use_actions"]
    assert 'export DISCOGS_TOKEN="your_discogs_personal_token"' in report["next_steps"]
    assert 'pip install -e ".[spotify]"' in report["next_steps"]


def test_setup_report_ready_when_discogs_and_spotify_are_configured(
    isolated_xdg, monkeypatch
):
    monkeypatch.setenv("DISCOGS_TOKEN", "discogs-token")
    monkeypatch.setattr(
        setup_report,
        "get_capabilities",
        lambda: AppCapabilities(
            spotify=SpotifyCapabilities(
                addon_available=True,
                configured=True,
                action_label="Spotify Ready",
                status_message="Spotify playback and matching are available.",
            )
        ),
    )

    conn = get_connection()
    try:
        upsert_releases(conn, [_release(111)])
    finally:
        conn.close()

    report = setup_report.run_setup_report()

    assert report["profile"] == "plus"
    assert report["onboarding_stage"] == "ready"
    assert report["discogs"]["configured"] is True
    assert report["discogs"]["token_source"] == "environment"
    assert report["collection"]["release_count_active"] == 1
    assert report["spotify"]["configured"] is True
    assert "addon_available" in report["spotify"]
    assert "action_label" in report["spotify"]
    assert "status_message" in report["spotify"]
    readiness = report["provider_readiness"]
    assert readiness["summary"]["required_services_configured"] is True
    assert readiness["summary"]["collection_synced"] is True
    checklist = report["first_run_checklist"]
    assert checklist["discogs_configured"] is True
    assert checklist["collection_synced"] is True
    assert checklist["spotify_addon_available"] is True
    assert checklist["spotify_configured"] is True
    assert checklist["ready_for_daily_use"] is True
    assert report["spotify"]["dashboard_url"] == "https://developer.spotify.com/dashboard"
    assert any("dplayer spin" in str(step) for step in report["daily_use_actions"])
    assert "dplayer devices --json" in report["next_steps"]


def test_setup_report_spotify_auth_next_steps_include_redirect_uri(
    isolated_xdg, monkeypatch
):
    monkeypatch.setenv("DISCOGS_TOKEN", "discogs-token")
    monkeypatch.setattr(
        setup_report,
        "get_capabilities",
        lambda: AppCapabilities(
            spotify=SpotifyCapabilities(
                addon_available=True,
                configured=False,
                action_label="Connect Spotify",
                status_message="Spotify addon is installed but not configured.",
            )
        ),
    )

    conn = get_connection()
    try:
        upsert_releases(conn, [_release(333)])
    finally:
        conn.close()

    report = setup_report.run_setup_report()

    assert report["profile"] == "plus"
    assert report["onboarding_stage"] == "needs_spotify_auth"
    assert report["spotify"]["configured"] is False
    assert "addon_available" in report["spotify"]
    assert "action_label" in report["spotify"]
    assert "status_message" in report["spotify"]
    readiness = report["provider_readiness"]
    assert isinstance(readiness.get("providers"), list)
    assert readiness["summary"]["ready_provider_count"] == 0
    checklist = report["first_run_checklist"]
    assert checklist["discogs_configured"] is True
    assert checklist["collection_synced"] is True
    assert checklist["spotify_addon_available"] is True
    assert checklist["spotify_configured"] is False
    assert checklist["ready_for_daily_use"] is False
    assert any(
        "http://127.0.0.1:8765/callback" in str(step)
        for step in report["next_steps"]
    )
    assert any(
        "https://developer.spotify.com/dashboard" in str(step)
        for step in report["next_steps"]
    )
    assert (
        report["spotify"]["oauth_guide_url"]
        == "https://developer.spotify.com/documentation/web-api/tutorials/code-flow"
    )
    assert any("Optional: connect Spotify" in str(step) for step in report["daily_use_actions"])
    assert "dplayer auth spotify-doctor" in report["next_steps"]


# ── Regression tests for bug fixes ──────────────────────────────────────────

def test_token_source_reports_app_settings_for_canonical_key(isolated_xdg, monkeypatch):
    """Token stored under canonical 'discogs_token' key should report app_settings."""
    monkeypatch.delenv("DISCOGS_TOKEN", raising=False)
    conn = get_connection()
    try:
        set_setting("discogs_token", "my_token", conn=conn)
    finally:
        conn.close()

    source = _discogs_token_source()
    assert source == "app_settings", f"Expected 'app_settings', got '{source}'"


def test_token_source_reports_app_settings_for_alias_key(isolated_xdg, monkeypatch):
    """Token stored under alias 'DISCOGS_TOKEN' DB key should report app_settings, not environment."""
    monkeypatch.delenv("DISCOGS_TOKEN", raising=False)
    conn = get_connection()
    try:
        # Simulate token stored under the uppercase alias key (edge case)
        set_setting("DISCOGS_TOKEN", "my_alias_token", conn=conn)
    finally:
        conn.close()

    source = _discogs_token_source()
    # Must not incorrectly return "environment" — the env var is not set
    assert source == "app_settings", f"Fallthrough should return 'app_settings', got '{source}'"


def test_token_source_reports_environment_for_env_var(isolated_xdg, monkeypatch):
    """Token from env var should report environment."""
    monkeypatch.setenv("DISCOGS_TOKEN", "env_token")
    source = _discogs_token_source()
    assert source == "environment"


def test_token_source_reports_missing_when_no_token(isolated_xdg, monkeypatch):
    """No token anywhere should report missing."""
    monkeypatch.delenv("DISCOGS_TOKEN", raising=False)
    source = _discogs_token_source()
    assert source == "missing"
