from __future__ import annotations

from discogs_player.capabilities import AppCapabilities, SpotifyCapabilities
from discogs_player.data.db import get_connection
from discogs_player.data.repo import upsert_releases
from discogs_player.use_cases import setup_report


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
    checklist = report["first_run_checklist"]
    assert checklist["discogs_configured"] is True
    assert checklist["collection_synced"] is True
    assert checklist["spotify_addon_available"] is True
    assert checklist["spotify_configured"] is True
    assert checklist["ready_for_daily_use"] is True
    assert report["spotify"]["dashboard_url"] == "https://developer.spotify.com/dashboard"
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
    assert "dplayer auth spotify-doctor" in report["next_steps"]
