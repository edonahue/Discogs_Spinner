from __future__ import annotations

import json

from discogs_player.use_cases.external_match_fallback import resolve_external_fallback_match


def test_resolve_external_fallback_match_from_audit_report(isolated_xdg):
    reports_dir = isolated_xdg["data"] / "discogs_player" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / "spotify_match_audit_single_live.json"
    report_path.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "discogs_release_id": 123,
                        "status": "review_queue",
                        "candidate_album_id": "714ndVxSx8lIWhQxdbcXIs",
                        "confidence": 0.81,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    release = {
        "discogs_release_id": 123,
        "artist": "Black Sabbath",
        "title": "Paranoid",
    }
    match = resolve_external_fallback_match(release)
    assert match is not None
    assert match.spotify_album_id == "714ndVxSx8lIWhQxdbcXIs"
    assert match.source == "audit-report:spotify_match_audit_single_live.json"
    assert match.confidence >= 0.8


def test_resolve_external_fallback_match_from_bootstrap_file(isolated_xdg, monkeypatch):
    bootstrap_path = isolated_xdg["data"] / "bootstrap_source.json"
    bootstrap_path.write_text(
        json.dumps(
            [
                {
                    "discogs_release_id": 456,
                    "spotify_album_id": "1A2GTWGtFfWp7KSQTwWOyo",
                    "confidence": 0.77,
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("DP_SPOTIFY_FALLBACK_BOOTSTRAP_PATHS", str(bootstrap_path))

    release = {
        "discogs_release_id": 456,
        "artist": "Example Artist",
        "title": "Example Title",
    }
    match = resolve_external_fallback_match(release)
    assert match is not None
    assert match.spotify_album_id == "1A2GTWGtFfWp7KSQTwWOyo"
    assert match.source == f"bootstrap:{bootstrap_path.name}"
    assert match.confidence >= 0.7

