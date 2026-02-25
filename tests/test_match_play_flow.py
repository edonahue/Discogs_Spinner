from __future__ import annotations

from discogs_player.use_cases import match_play_flow


def test_run_match_action_reports_matched_candidate(monkeypatch):
    monkeypatch.setattr(
        match_play_flow,
        "run_match_release",
        lambda release_id, threshold=0.72, max_retries=0, backoff_seconds=1.0: {
            "discogs_release_id": release_id,
            "matched": True,
            "spotify_album_id": "album-123",
            "confidence": 0.9345,
            "source": "auto",
            "best_candidate": {
                "name": "Nevermind",
                "artists": ["Nirvana"],
                "release_date": "1991-09-24",
            },
        },
    )

    payload = match_play_flow.run_match_action(7)

    assert payload["matched"] is True
    assert payload["spotify_album_id"] == "album-123"
    assert "Matched release 7 to album-123" in str(payload["status_message"])
    assert payload["candidate_summary"] == "Nevermind - Nirvana - 1991-09-24"


def test_run_match_action_reports_unmatched(monkeypatch):
    monkeypatch.setattr(
        match_play_flow,
        "run_match_release",
        lambda release_id, threshold=0.72, max_retries=0, backoff_seconds=1.0: {
            "discogs_release_id": release_id,
            "matched": False,
            "spotify_album_id": None,
            "confidence": 0.41,
            "source": "auto",
            "best_candidate": {
                "name": "Low Match",
                "artists": ["Various"],
                "release_date": "2019-01-01",
            },
        },
    )

    payload = match_play_flow.run_match_action(11)
    assert payload["matched"] is False
    assert "No confident match for release 11" in str(payload["status_message"])
    assert payload["candidate_summary"] == "Low Match - Various - 2019-01-01"


def test_run_match_action_uses_interactive_retry_profile(monkeypatch):
    captured: dict[str, object] = {}

    def _fake_match_release(
        release_id: int,
        *,
        threshold: float = 0.72,
        max_retries: int = 5,
        backoff_seconds: float = 2.0,
        external_fallback: bool = True,
    ) -> dict[str, object]:
        captured["release_id"] = release_id
        captured["threshold"] = threshold
        captured["max_retries"] = max_retries
        captured["backoff_seconds"] = backoff_seconds
        captured["external_fallback"] = external_fallback
        return {
            "discogs_release_id": release_id,
            "matched": False,
            "spotify_album_id": None,
            "confidence": 0.0,
            "source": "auto",
            "best_candidate": None,
        }

    monkeypatch.setattr(match_play_flow, "run_match_release", _fake_match_release)
    match_play_flow.run_match_action(77)

    assert captured["release_id"] == 77
    assert captured["threshold"] == 0.72
    assert captured["max_retries"] == 0
    assert captured["backoff_seconds"] == 1.0


def test_run_override_action_reports_saved_mapping(monkeypatch):
    monkeypatch.setattr(
        match_play_flow,
        "run_match_override",
        lambda release_id, spotify_album_id: {
            "discogs_release_id": release_id,
            "spotify_album_id": "override-1",
            "confidence": 1.0,
            "is_override": True,
        },
    )

    payload = match_play_flow.run_override_action(22, "spotify:album:override-1")
    assert payload["spotify_album_id"] == "override-1"
    assert payload["is_override"] is True
    assert "Override saved for release 22" in str(payload["status_message"])


def test_run_play_action_starts_playback(monkeypatch):
    captured: dict[str, object] = {}

    def _fake_run_play_release(**kwargs):
        captured.update(kwargs)
        return {
            "discogs_release_id": 44,
            "spotify_album_id": "album-44",
            "playback_started": True,
            "device_name": "Desk",
            "device_id": "desk-1",
            "fallback_reason": None,
            "fallback_open_url": None,
        }

    monkeypatch.setattr(match_play_flow, "run_play_release", _fake_run_play_release)

    payload = match_play_flow.run_play_action(44)

    assert captured == {
        "discogs_release_id": 44,
        "auto_match": True,
        "open_fallback": True,
    }
    assert payload["playback_started"] is True
    assert "Playback started on Desk: album-44" == payload["status_message"]


def test_run_play_action_reports_fallback(monkeypatch):
    monkeypatch.setattr(
        match_play_flow,
        "run_play_release",
        lambda **kwargs: {
            "discogs_release_id": kwargs["discogs_release_id"],
            "spotify_album_id": None,
            "playback_started": False,
            "fallback_reason": "missing_mapping",
            "fallback_open_url": "https://open.spotify.com/search/Test",
            "message": "No mapping found.",
        },
    )

    payload = match_play_flow.run_play_action(55)
    assert payload["playback_started"] is False
    assert payload["fallback_reason"] == "missing_mapping"
    assert (
        "No mapping found. Open URL: https://open.spotify.com/search/Test"
        == payload["status_message"]
    )


def test_run_match_audit_action_reports_summary(monkeypatch):
    monkeypatch.setattr(
        match_play_flow,
        "run_match_audit",
        lambda **kwargs: {
            "run_processed_count": 12,
            "run_auto_applied_count": 7,
            "run_review_queue_count": 4,
            "run_error_count": 1,
            "report_path": "/tmp/audit.json",
            **kwargs,
        },
    )

    payload = match_play_flow.run_match_audit_action(apply_safe_matches=True)
    assert payload["action"] == "match_audit"
    assert payload["run_processed_count"] == 12
    assert payload["run_auto_applied_count"] == 7
    assert payload["report_path"] == "/tmp/audit.json"
    assert "safe apply + audit complete" in str(payload["status_message"])


def test_run_match_review_apply_action_reports_summary(monkeypatch):
    monkeypatch.setattr(
        match_play_flow,
        "run_match_audit_review_action",
        lambda **kwargs: {
            "action": kwargs["action"],
            "updated_count": 3,
            "report_path": "/tmp/audit.json",
        },
    )

    payload = match_play_flow.run_match_review_apply_action(apply_all=True)
    assert payload["action"] == "match_review_apply"
    assert payload["updated_count"] == 3
    assert payload["report_path"] == "/tmp/audit.json"
    assert "Applied 3 review candidate mappings." == payload["status_message"]


def test_run_match_retry_errors_action_reports_summary(monkeypatch):
    monkeypatch.setattr(
        match_play_flow,
        "run_match_audit_retry_errors",
        lambda **kwargs: {
            "run_processed_count": 5,
            "run_error_count": 1,
            **kwargs,
            "report_path": "/tmp/audit.json",
        },
    )

    payload = match_play_flow.run_match_retry_errors_action(limit=50)
    assert payload["action"] == "match_retry_errors"
    assert payload["run_processed_count"] == 5
    assert payload["run_error_count"] == 1
    assert payload["report_path"] == "/tmp/audit.json"
