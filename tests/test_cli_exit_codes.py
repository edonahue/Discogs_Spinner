from __future__ import annotations

import json

from typer.testing import CliRunner

from discogs_player.cli import commands
from discogs_player.services.sync_manager import MissingDiscogsTokenError

runner = CliRunner()


def test_sync_missing_discogs_token_exits_3(isolated_xdg, monkeypatch):
    def _raise_missing_token(**kwargs):
        _ = kwargs
        raise MissingDiscogsTokenError("DISCOGS_TOKEN is not set")

    monkeypatch.setattr(
        "discogs_player.use_cases.sync_collection.run_sync_collection",
        _raise_missing_token,
    )
    result = runner.invoke(commands.app, ["sync"])
    assert result.exit_code == 3
    assert "DISCOGS_TOKEN is not set" in result.output


def test_devices_auth_error_exits_3(monkeypatch):
    def _raise_auth_error():
        raise commands.SpotifyAuthError("Spotify token missing")

    monkeypatch.setattr(commands, "run_list_devices", _raise_auth_error)
    result = runner.invoke(commands.app, ["devices"])
    assert result.exit_code == 3
    assert "Spotify token missing" in result.output


def test_play_missing_mapping_exits_5(monkeypatch):
    def _raise_missing_mapping(**kwargs):
        _ = kwargs
        raise commands.MissingSpotifyMappingError("No mapping exists")

    monkeypatch.setattr(commands, "run_play_release", _raise_missing_mapping)
    result = runner.invoke(commands.app, ["play", "123"])
    assert result.exit_code == 5
    assert "No mapping exists" in result.output


def test_play_spotify_api_error_exits_4(monkeypatch):
    def _raise_api_error(**kwargs):
        _ = kwargs
        raise commands.SpotifyApiError("Spotify API unavailable")

    monkeypatch.setattr(commands, "run_play_release", _raise_api_error)
    result = runner.invoke(commands.app, ["play", "123"])
    assert result.exit_code == 4
    assert "Spotify API unavailable" in result.output


def test_auth_spotify_failure_exits_3(monkeypatch):
    def _raise_auth_error(**kwargs):
        _ = kwargs
        raise commands.SpotifyAuthError("OAuth rejected")

    monkeypatch.setattr(commands, "run_spotify_oauth_login", _raise_auth_error)
    result = runner.invoke(commands.app, ["auth", "spotify"])
    assert result.exit_code == 3
    assert "OAuth rejected" in result.output


def test_auth_spotify_manual_json_requires_callback_or_code():
    result = runner.invoke(commands.app, ["auth", "spotify", "--manual", "--json"])
    assert result.exit_code == 2
    assert "requires --callback-url or --code" in result.output


def test_auth_spotify_manual_callback_url_forwards_kwargs(monkeypatch):
    captured: dict[str, object] = {}

    def _fake_oauth_login(**kwargs):
        captured.update(kwargs)
        return {"ok": True}

    monkeypatch.setattr(commands, "run_spotify_oauth_login", _fake_oauth_login)
    result = runner.invoke(
        commands.app,
        [
            "auth",
            "spotify",
            "--manual",
            "--callback-url",
            "http://127.0.0.1:8765/callback?code=abc&state=def",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert captured["manual_mode"] is True
    assert captured["manual_callback_url"] == (
        "http://127.0.0.1:8765/callback?code=abc&state=def"
    )
    assert captured["manual_code"] is None
    assert captured["allow_manual_fallback"] is False


def test_auth_spotify_doctor_json_output(monkeypatch):
    monkeypatch.setattr(
        commands,
        "run_spotify_auth_diagnostics",
        lambda **kwargs: {
            "backend": "spotify",
            "addon_available": True,
            "configured": True,
            "keyring_available": True,
            "expected_redirect_uri": "http://127.0.0.1:8765/callback",
            "recommended_action": "Run dplayer devices --json",
            "credentials": {
                "client_id_available": True,
                "client_secret_available": True,
                "refresh_token_available": True,
            },
            "access_token": {"available": True, "fresh": True},
        },
    )
    monkeypatch.setattr(commands, "run_list_devices", lambda: [{"id": "device-1"}])

    result = runner.invoke(commands.app, ["auth", "spotify-doctor", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["device_probe_attempted"] is True
    assert payload["device_probe_ok"] is True
    assert payload["device_count"] == 1


def test_match_audit_json_forwards_options(monkeypatch):
    captured: dict[str, object] = {}

    def _run_match_audit(**kwargs):
        captured.update(kwargs)
        return {"run_processed_count": 0, "review_queue": [], "errors": []}

    monkeypatch.setattr(commands, "run_match_audit", _run_match_audit)
    result = runner.invoke(
        commands.app,
        [
            "match",
            "audit",
            "--limit",
            "40",
            "--threshold",
            "0.72",
            "--auto-apply-threshold",
            "0.9",
            "--apply-safe",
            "--resume",
            "--report",
            "/tmp/audit.json",
            "--request-delay-seconds",
            "0.2",
            "--max-retries",
            "3",
            "--backoff-seconds",
            "1.5",
            "--compact",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert json.loads(result.output)["run_processed_count"] == 0
    assert captured == {
        "scope": "collection",
        "limit": 40,
        "review_threshold": 0.72,
        "auto_apply_threshold": 0.9,
        "apply_safe_matches": True,
        "resume": True,
        "report_path": "/tmp/audit.json",
        "request_delay_seconds": 0.2,
        "max_retries": 3,
        "backoff_seconds": 1.5,
        "retry_errors_on_resume": True,
        "compact_output": True,
        "progress_log_path": None,
    }


def test_match_audit_disallows_unmatched_flag():
    result = runner.invoke(commands.app, ["match", "audit", "--unmatched"])
    assert result.exit_code == 2
    assert "Do not combine --unmatched with `match audit`." in result.output


def test_match_unmatched_forwards_scope(monkeypatch):
    captured: dict[str, object] = {}

    def _run_match_unmatched(**kwargs):
        captured.update(kwargs)
        return {
            "processed_count": 0,
            "matched_count": 0,
            "review_count": 0,
            "error_count": 0,
            "results": [],
        }

    monkeypatch.setattr(commands, "run_match_unmatched", _run_match_unmatched)
    result = runner.invoke(
        commands.app,
        [
            "match",
            "--unmatched",
            "--scope",
            "wantlist",
            "--limit",
            "10",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert captured == {
        "limit": 10,
        "scope": "wantlist",
        "threshold": 0.72,
        "auto_apply_threshold": 0.9,
    }


def test_review_list_json_output(monkeypatch):
    expected = {
        "ok": True,
        "report_path": "/tmp/audit.json",
        "review_count": 3,
        "error_count": 1,
        "manual_applied_count": 2,
        "manual_rejected_count": 1,
        "review_queue": [],
        "errors": [],
    }
    captured: dict[str, object] = {}

    def _run_match_audit_review_list(**kwargs):
        captured.update(kwargs)
        return expected

    monkeypatch.setattr(
        commands, "run_match_audit_review_list", _run_match_audit_review_list
    )
    result = runner.invoke(
        commands.app,
        [
            "review",
            "list",
            "--report",
            "/tmp/audit.json",
            "--limit",
            "25",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert json.loads(result.output) == expected
    assert captured == {"report_path": "/tmp/audit.json", "limit": 25}


def test_review_apply_json_output(monkeypatch):
    expected = {
        "ok": True,
        "action": "apply",
        "report_path": "/tmp/audit.json",
        "selected_count": 2,
        "updated_count": 2,
        "run_manual_applied_count": 2,
        "run_manual_rejected_count": 0,
        "run_review_queue_count": 1,
        "review_queue_count": 1,
        "status_message": "Applied selected review candidates.",
    }
    captured: dict[str, object] = {}

    def _run_match_audit_review_action(**kwargs):
        captured.update(kwargs)
        return expected

    monkeypatch.setattr(
        commands, "run_match_audit_review_action", _run_match_audit_review_action
    )
    result = runner.invoke(
        commands.app,
        [
            "review",
            "apply",
            "--release-id",
            "101",
            "--release-id",
            "102",
            "--report",
            "/tmp/audit.json",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert json.loads(result.output) == expected
    assert captured == {
        "action": "apply",
        "report_path": "/tmp/audit.json",
        "release_ids": [101, 102],
        "apply_all": False,
    }


def test_review_reject_requires_selection():
    result = runner.invoke(commands.app, ["review", "reject"])
    assert result.exit_code == 2
    assert "Provide --all or at least one --release-id." in result.output


def test_review_retry_errors_json_output(monkeypatch):
    captured: dict[str, object] = {}

    def _run_match_audit_retry_errors(**kwargs):
        captured.update(kwargs)
        return {"run_processed_count": 4, "run_error_count": 1, "report_path": "/tmp/audit.json"}

    monkeypatch.setattr(
        commands, "run_match_audit_retry_errors", _run_match_audit_retry_errors
    )
    result = runner.invoke(
        commands.app,
        [
            "review",
            "retry-errors",
            "--report",
            "/tmp/audit.json",
            "--limit",
            "50",
            "--request-delay-seconds",
            "0.1",
            "--max-retries",
            "2",
            "--backoff-seconds",
            "0.5",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert json.loads(result.output)["run_processed_count"] == 4
    assert captured == {
        "report_path": "/tmp/audit.json",
        "limit": 50,
        "scope": None,
        "request_delay_seconds": 0.1,
        "max_retries": 2,
        "backoff_seconds": 0.5,
        "apply_safe_matches": False,
    }


def test_setup_json_output(monkeypatch):
    expected = {
        "profile": "plus",
        "onboarding_stage": "ready",
        "discogs": {"configured": True, "token_source": "environment"},
        "collection": {"release_count_active": 10, "release_count_total": 10},
        "spotify": {
            "addon_available": True,
            "configured": True,
            "action_label": "Spotify Ready",
        },
        "next_steps": ["./scripts/spotify_live_smoke.sh"],
    }
    monkeypatch.setattr(commands, "run_setup_report", lambda: expected)

    result = runner.invoke(commands.app, ["setup", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.output) == expected


def test_setup_table_output_includes_setup_links(monkeypatch):
    expected = {
        "profile": "plus",
        "onboarding_stage": "needs_spotify_auth",
        "discogs": {
            "configured": True,
            "token_source": "environment",
            "status_message": "Discogs token configured.",
            "token_setup_url": "https://www.discogs.com/settings/developers",
        },
        "collection": {"release_count_active": 10, "last_sync_time": None},
        "spotify": {
            "addon_available": True,
            "configured": False,
            "status_message": "Connect Spotify.",
            "next_action": "Run auth flow.",
            "dashboard_url": "https://developer.spotify.com/dashboard",
            "oauth_guide_url": "https://developer.spotify.com/documentation/web-api/tutorials/code-flow",
            "redirect_uri": "http://127.0.0.1:8765/callback",
        },
        "links": {
            "discogs_token_url": "https://www.discogs.com/settings/developers",
            "spotify_dashboard_url": "https://developer.spotify.com/dashboard",
            "spotify_oauth_guide_url": "https://developer.spotify.com/documentation/web-api/tutorials/code-flow",
        },
        "next_steps": ["dplayer auth spotify-doctor"],
    }
    monkeypatch.setattr(commands, "run_setup_report", lambda: expected)

    result = runner.invoke(commands.app, ["setup"])

    assert result.exit_code == 0
    assert "discogs_token_url" in result.output
    assert "spotify_dashboard_url" in result.output
    assert "spotify_oauth_guide_url" in result.output
    assert "links_discogs_token_url" in result.output


def test_analytics_json_output(monkeypatch):
    expected = {
        "release_count_active": 12,
        "mapped_count": 8,
        "unmatched_count": 4,
        "top_limit": 7,
        "by_release_year": [{"year": 1991, "count": 2}],
        "acquisition_timeline": [{"year": 2026, "count": 12}],
        "top_genres": [{"genre": "Rock", "count": 9}],
        "top_styles": [{"style": "Grunge", "count": 3}],
        "top_artists": [{"artist": "Nirvana", "count": 2}],
    }

    def _run_collection_analytics(*, limit: int):
        assert limit == 7
        return expected

    monkeypatch.setattr(commands, "run_collection_analytics", _run_collection_analytics)
    result = runner.invoke(commands.app, ["analytics", "--limit", "7", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.output) == expected


def test_analytics_value_error_exits_2(monkeypatch):
    def _run_collection_analytics(*, limit: int):
        _ = limit
        raise ValueError("limit must be >= 1")

    monkeypatch.setattr(commands, "run_collection_analytics", _run_collection_analytics)
    result = runner.invoke(commands.app, ["analytics"])

    assert result.exit_code == 2
    assert "limit must be >= 1" in result.output


def test_import_json_output(monkeypatch):
    expected = {
        "ok": True,
        "input_path": "/tmp/snapshot.json",
        "dry_run": True,
        "conflict_mode": "merge",
        "include_settings": False,
        "snapshot_schema_version": 1,
        "payload_release_count": 12,
        "imported_release_count": 12,
        "imported_mapping_count": 9,
        "imported_market_price_count": 6,
        "imported_settings_count": 0,
        "pre_import_release_count_total": 4,
        "pre_import_release_count_active": 4,
        "pre_import_mapped_count": 1,
        "pre_import_settings_count": 3,
    }

    def _run_import_collection(**kwargs):
        assert kwargs["input_path"] == "/tmp/snapshot.json"
        assert kwargs["conflict_mode"] == "merge"
        assert kwargs["dry_run"] is True
        assert kwargs["include_settings"] is False
        return expected

    monkeypatch.setattr(commands, "run_import_collection", _run_import_collection)
    result = runner.invoke(
        commands.app,
        [
            "import",
            "--input",
            "/tmp/snapshot.json",
            "--dry-run",
            "--no-settings",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert json.loads(result.output) == expected


def test_import_validation_error_exits_2(monkeypatch):
    def _run_import_collection(**kwargs):
        _ = kwargs
        raise ValueError("Conflict mode must be 'merge' or 'replace'.")

    monkeypatch.setattr(commands, "run_import_collection", _run_import_collection)
    result = runner.invoke(commands.app, ["import", "--input", "/tmp/snapshot.json"])

    assert result.exit_code == 2
    assert "Conflict mode must be 'merge' or 'replace'." in result.output


def test_bootstrap_import_json_output(monkeypatch):
    expected = {
        "ok": True,
        "input_path": "/tmp/bootstrap.json",
        "input_kind": "json",
        "source_format_requested": "auto",
        "source_format_used": "discofy",
        "conflict_mode": "merge",
        "dry_run": True,
        "default_confidence": 0.88,
        "mark_override": False,
        "skip_missing_releases": True,
        "parsed_mapping_count": 4,
        "invalid_row_count": 1,
        "duplicate_row_count": 0,
        "imported_mapping_count": 3,
        "skipped_missing_release_count": 1,
        "skipped_existing_mapping_count": 0,
        "skipped_override_mapping_count": 0,
        "pre_import_release_count_total": 10,
        "pre_import_release_count_active": 10,
        "pre_import_mapped_count": 2,
        "pre_import_mapping_row_count": 2,
        "preview": [],
    }
    captured: dict[str, object] = {}

    def _run_bootstrap_mapping_import(**kwargs):
        captured.update(kwargs)
        return expected

    monkeypatch.setattr(
        commands, "run_bootstrap_mapping_import", _run_bootstrap_mapping_import
    )
    result = runner.invoke(
        commands.app,
        [
            "bootstrap",
            "import",
            "--input",
            "/tmp/bootstrap.json",
            "--format",
            "auto",
            "--conflict-mode",
            "merge",
            "--dry-run",
            "--default-confidence",
            "0.88",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert json.loads(result.output) == expected
    assert captured == {
        "input_path": "/tmp/bootstrap.json",
        "source_format": "auto",
        "conflict_mode": "merge",
        "dry_run": True,
        "default_confidence": 0.88,
        "mark_override": False,
        "skip_missing_releases": True,
    }


def test_bootstrap_import_validation_error_exits_2(monkeypatch):
    def _run_bootstrap_mapping_import(**kwargs):
        _ = kwargs
        raise ValueError("No bootstrap mappings found.")

    monkeypatch.setattr(
        commands, "run_bootstrap_mapping_import", _run_bootstrap_mapping_import
    )
    result = runner.invoke(
        commands.app, ["bootstrap", "import", "--input", "/tmp/bootstrap.json"]
    )

    assert result.exit_code == 2
    assert "No bootstrap mappings found." in result.output


def test_art_status_json_output(monkeypatch):
    monkeypatch.setattr(commands, "get_high_res_art_preference", lambda: (True, 1500))

    result = runner.invoke(commands.app, ["art", "status", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["enabled"] is True
    assert payload["target_size"] == 1500
    assert payload["enabled_setting_key"] == "high_res_art_enabled"
    assert payload["target_size_setting_key"] == "high_res_art_target_size"


def test_art_refresh_json_forwards_options_and_persists_opt_in(monkeypatch):
    captured: dict[str, object] = {}
    config_calls: list[tuple[str, str]] = []

    def _run_refresh_high_res_art(**kwargs):
        captured.update(kwargs)
        return {
            "scope": kwargs["scope"],
            "limit": kwargs["limit"],
            "target_size": kwargs["target_size"],
            "workers": kwargs["workers"],
            "dry_run": kwargs["dry_run"],
            "scanned_count": 5,
            "eligible_count": 4,
            "unique_upgraded_url_count": 3,
            "warmed_url_count": 0,
            "failed_url_count": 0,
            "warmed_release_count": 0,
            "collection_scanned_count": 5,
            "wantlist_scanned_count": 0,
        }

    def _run_config_set(key: str, value: str):
        config_calls.append((key, value))
        return {"key": key, "value": value}

    monkeypatch.setattr(commands, "run_refresh_high_res_art", _run_refresh_high_res_art)
    monkeypatch.setattr(commands, "run_config_set", _run_config_set)
    monkeypatch.setattr(commands, "get_high_res_art_preference", lambda: (True, 1300))

    result = runner.invoke(
        commands.app,
        [
            "art",
            "refresh",
            "--scope",
            "both",
            "--limit",
            "20",
            "--target-size",
            "1300",
            "--workers",
            "4",
            "--dry-run",
            "--enable",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert captured == {
        "scope": "both",
        "limit": 20,
        "target_size": 1300,
        "workers": 4,
        "dry_run": True,
    }
    assert config_calls == [
        ("high_res_art_enabled", "1"),
        ("high_res_art_target_size", "1300"),
    ]
    payload = json.loads(result.output)
    assert payload["enabled"] is True
    assert payload["configured_target_size"] == 1300


def test_art_refresh_rejects_enable_disable_combination():
    result = runner.invoke(commands.app, ["art", "refresh", "--enable", "--disable"])

    assert result.exit_code == 2
    assert "Do not combine --enable and --disable" in result.output


def test_wantlist_sync_missing_discogs_token_exits_3(monkeypatch):
    def _raise_missing_token(**kwargs):
        _ = kwargs
        raise MissingDiscogsTokenError("DISCOGS_TOKEN is not set")

    monkeypatch.setattr(commands, "run_sync_wantlist", _raise_missing_token)
    result = runner.invoke(commands.app, ["wantlist", "sync"])

    assert result.exit_code == 3
    assert "DISCOGS_TOKEN is not set" in result.output


def test_wantlist_sync_full_and_verbose_are_forwarded(monkeypatch):
    captured: dict[str, object] = {}

    def _run_sync_wantlist(**kwargs):
        captured.update(kwargs)
        progress_callback = kwargs.get("progress_callback")
        if callable(progress_callback):
            progress_callback(2, 5, 50, 120)
        return {
            "fetched_count": 120,
            "upserted_count": 120,
            "deactivated_count": 0,
            "last_sync_time": "2026-02-20T00:00:00+00:00",
            "skipped_empty_deactivate": False,
            "warnings": [],
        }

    monkeypatch.setattr(commands, "run_sync_wantlist", _run_sync_wantlist)
    result = runner.invoke(commands.app, ["wantlist", "sync", "--full", "--verbose"])

    assert result.exit_code == 0
    assert captured["allow_empty_deactivate"] is True
    assert callable(captured["progress_callback"])
    assert "Fetched wantlist page 2/5: 50 releases (total=120)" in result.output


def test_wantlist_sync_json_default_forwarding(monkeypatch):
    captured: dict[str, object] = {}
    expected = {
        "fetched_count": 0,
        "upserted_count": 0,
        "deactivated_count": 0,
        "last_sync_time": "2026-02-20T00:00:00+00:00",
        "skipped_empty_deactivate": True,
        "warnings": ["Skipped deactivate on empty wantlist response."],
    }

    def _run_sync_wantlist(**kwargs):
        captured.update(kwargs)
        return expected

    monkeypatch.setattr(commands, "run_sync_wantlist", _run_sync_wantlist)
    result = runner.invoke(commands.app, ["wantlist", "sync", "--json"])

    assert result.exit_code == 0
    assert captured["allow_empty_deactivate"] is False
    assert captured["progress_callback"] is None
    assert json.loads(result.output) == expected


def test_wantlist_list_json_output(monkeypatch):
    expected = [
        {
            "discogs_release_id": 123,
            "artist": "The Clash",
            "title": "London Calling",
            "year": 1979,
            "genres": ["Rock"],
            "styles": ["Punk"],
            "thumb_url": None,
            "cover_url": None,
            "notes": "US pressing",
            "added_at": "2026-02-07T00:00:00+00:00",
            "last_synced_at": "2026-02-07T00:00:00+00:00",
            "is_active": True,
        }
    ]

    def _run_list_wantlist(**kwargs):
        assert kwargs["limit"] == 10
        assert kwargs["q"] == "clash"
        assert kwargs["year"] == "1970:1979"
        assert kwargs["genres"] == ["Rock"]
        assert kwargs["styles"] == ["Punk"]
        assert kwargs["with_value"] is False
        return expected

    monkeypatch.setattr(commands, "run_list_wantlist", _run_list_wantlist)
    result = runner.invoke(
        commands.app,
        [
            "wantlist",
            "list",
            "--limit",
            "10",
            "--q",
            "clash",
            "--year",
            "1970:1979",
            "--genre",
            "Rock",
            "--style",
            "Punk",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert json.loads(result.output) == expected


def test_wantlist_list_with_value_is_forwarded(monkeypatch):
    expected = [
        {"discogs_release_id": 777, "artist": "A", "title": "B", "market_median": 12.5}
    ]

    def _run_list_wantlist(**kwargs):
        assert kwargs["with_value"] is True
        return expected

    monkeypatch.setattr(commands, "run_list_wantlist", _run_list_wantlist)
    result = runner.invoke(commands.app, ["wantlist", "list", "--with-value", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.output) == expected


def test_list_with_value_is_forwarded(monkeypatch):
    expected = [
        {"discogs_release_id": 888, "artist": "A", "title": "B", "market_median": 21.0}
    ]

    def _run_list_releases(**kwargs):
        assert kwargs["with_value"] is True
        assert kwargs["unmatched"] is False
        return expected

    monkeypatch.setattr(commands, "run_list_releases", _run_list_releases)
    result = runner.invoke(commands.app, ["list", "--with-value", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.output) == expected


def test_value_status_json_output(monkeypatch):
    expected = {
        "active_release_count": 10,
        "priced_release_count": 7,
        "unpriced_release_count": 3,
        "total_lowest": 100.5,
        "total_median": 140.75,
        "total_highest": 180.25,
        "market_value_last_updated": "2026-02-07T00:00:00+00:00",
        "currency_counts": [{"currency": "USD", "count": 7}],
    }

    monkeypatch.setattr(commands, "run_market_value_status", lambda: expected)
    result = runner.invoke(commands.app, ["value", "status", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.output) == expected


def test_value_status_table_renders_artist_and_album_examples(monkeypatch):
    summary = {
        "active_release_count": 2,
        "priced_release_count": 2,
        "unpriced_release_count": 0,
        "total_lowest": 100.0,
        "total_median": 120.0,
        "total_highest": 150.0,
        "market_value_last_updated": "2026-02-07T00:00:00+00:00",
        "currency_counts": [{"currency": "USD", "count": 2}],
    }
    examples = {
        "limit": 2,
        "high_priced": [
            {
                "discogs_release_id": 101,
                "artist": "High Artist",
                "title": "High Album",
                "market_median": 200.0,
                "market_lowest": 180.0,
                "market_highest": 220.0,
                "market_currency": "USD",
            }
        ],
        "low_priced": [
            {
                "discogs_release_id": 202,
                "artist": "Low Artist",
                "title": "Low Album",
                "market_median": 5.0,
                "market_lowest": 3.0,
                "market_highest": 7.0,
                "market_currency": "USD",
            }
        ],
    }

    monkeypatch.setattr(commands, "run_market_value_status", lambda: summary)
    monkeypatch.setattr(
        commands, "run_market_value_examples", lambda *, limit: examples
    )
    result = runner.invoke(commands.app, ["value", "status"])

    assert result.exit_code == 0
    assert "High Artist" in result.output
    assert "High Album" in result.output
    assert "Low Artist" in result.output
    assert "Low Album" in result.output


def test_value_examples_json_output(monkeypatch):
    expected = {
        "limit": 2,
        "high_priced": [{"discogs_release_id": 1, "artist": "A", "title": "High"}],
        "low_priced": [{"discogs_release_id": 2, "artist": "B", "title": "Low"}],
    }

    def _run_market_value_examples(*, limit: int):
        assert limit == 2
        return expected

    monkeypatch.setattr(
        commands, "run_market_value_examples", _run_market_value_examples
    )
    result = runner.invoke(
        commands.app, ["value", "examples", "--limit", "2", "--json"]
    )

    assert result.exit_code == 0
    assert json.loads(result.output) == expected


def test_value_snapshot_json_output(monkeypatch):
    expected = {
        "snapshot_id": 3,
        "captured_at": "2026-02-08T00:00:00+00:00",
        "active_release_count": 10,
        "priced_release_count": 8,
        "unpriced_release_count": 2,
        "total_lowest": 100.0,
        "total_median": 130.0,
        "total_highest": 160.0,
        "market_value_last_updated": "2026-02-07T00:00:00+00:00",
        "currency_counts": [{"currency": "USD", "count": 8}],
    }

    monkeypatch.setattr(commands, "run_market_value_snapshot", lambda: expected)
    result = runner.invoke(commands.app, ["value", "snapshot", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.output) == expected


def test_value_trend_json_output(monkeypatch):
    expected = {
        "snapshot_count": 2,
        "window_start": "2026-02-07T00:00:00+00:00",
        "window_end": "2026-02-08T00:00:00+00:00",
        "window_delta_total_median": 5.0,
        "window_delta_total_median_percent": 4.0,
        "points": [
            {
                "id": 1,
                "captured_at": "2026-02-07T00:00:00+00:00",
                "total_median": 125.0,
            },
            {
                "id": 2,
                "captured_at": "2026-02-08T00:00:00+00:00",
                "total_median": 130.0,
            },
        ],
    }

    def _run_market_value_trend(*, limit: int):
        assert limit == 12
        return expected

    monkeypatch.setattr(commands, "run_market_value_trend", _run_market_value_trend)
    result = runner.invoke(commands.app, ["value", "trend", "--limit", "12", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.output) == expected


def test_value_trend_validation_error_exits_2(monkeypatch):
    def _run_market_value_trend(*, limit: int):
        _ = limit
        raise ValueError("limit must be >= 1")

    monkeypatch.setattr(commands, "run_market_value_trend", _run_market_value_trend)
    result = runner.invoke(commands.app, ["value", "trend"])

    assert result.exit_code == 2
    assert "limit must be >= 1" in result.output


def test_value_show_json_output(monkeypatch):
    expected = {
        "discogs_release_id": 123,
        "artist": "The Clash",
        "title": "London Calling",
        "year": 1979,
        "is_active": True,
        "spotify_album_id": None,
        "market_lowest": 10.0,
        "market_median": 12.5,
        "market_highest": 15.0,
        "market_currency": "USD",
        "market_last_updated_at": "2026-02-07T00:00:00+00:00",
        "has_market_value": True,
    }

    def _run_market_value_show(release_id: int, *, refresh: bool):
        assert release_id == 123
        assert refresh is False
        return expected

    monkeypatch.setattr(commands, "run_market_value_show", _run_market_value_show)
    result = runner.invoke(commands.app, ["value", "show", "123", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.output) == expected


def test_value_show_validation_error_exits_2(monkeypatch):
    def _run_market_value_show(release_id: int, *, refresh: bool):
        _ = release_id
        _ = refresh
        raise ValueError("Release not found: 999")

    monkeypatch.setattr(commands, "run_market_value_show", _run_market_value_show)
    result = runner.invoke(commands.app, ["value", "show", "999"])

    assert result.exit_code == 2
    assert "Release not found: 999" in result.output


def test_value_show_refresh_is_forwarded(monkeypatch):
    captured: dict[str, object] = {}

    def _run_market_value_show(release_id: int, *, refresh: bool):
        captured["release_id"] = release_id
        captured["refresh"] = refresh
        return {"discogs_release_id": release_id}

    monkeypatch.setattr(commands, "run_market_value_show", _run_market_value_show)
    result = runner.invoke(
        commands.app, ["value", "show", "456", "--refresh", "--json"]
    )

    assert result.exit_code == 0
    assert captured == {"release_id": 456, "refresh": True}
    assert json.loads(result.output) == {"discogs_release_id": 456}


def test_value_show_refresh_missing_discogs_token_exits_3(monkeypatch):
    def _run_market_value_show(release_id: int, *, refresh: bool):
        _ = release_id
        _ = refresh
        raise MissingDiscogsTokenError("DISCOGS_TOKEN is not set")

    monkeypatch.setattr(commands, "run_market_value_show", _run_market_value_show)
    result = runner.invoke(commands.app, ["value", "show", "456", "--refresh"])

    assert result.exit_code == 3
    assert "DISCOGS_TOKEN is not set" in result.output


def test_value_missing_json_output(monkeypatch):
    expected = [{"discogs_release_id": 1}, {"discogs_release_id": 2}]

    def _run_market_value_missing(
        *, limit: int, stale_days: int | None, with_value: bool
    ):
        assert limit == 5
        assert stale_days is None
        assert with_value is False
        return expected

    monkeypatch.setattr(commands, "run_market_value_missing", _run_market_value_missing)
    result = runner.invoke(commands.app, ["value", "missing", "--limit", "5", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.output) == expected


def test_value_missing_validation_error_exits_2(monkeypatch):
    def _run_market_value_missing(
        *, limit: int, stale_days: int | None, with_value: bool
    ):
        _ = limit
        _ = stale_days
        _ = with_value
        raise ValueError("limit must be >= 1")

    monkeypatch.setattr(commands, "run_market_value_missing", _run_market_value_missing)
    result = runner.invoke(commands.app, ["value", "missing"])

    assert result.exit_code == 2
    assert "limit must be >= 1" in result.output


def test_value_missing_stale_and_with_value_are_forwarded(monkeypatch):
    captured: dict[str, object] = {}

    def _run_market_value_missing(
        *, limit: int, stale_days: int | None, with_value: bool
    ):
        captured["limit"] = limit
        captured["stale_days"] = stale_days
        captured["with_value"] = with_value
        return [{"discogs_release_id": 5, "market_need_reason": "stale"}]

    monkeypatch.setattr(commands, "run_market_value_missing", _run_market_value_missing)
    result = runner.invoke(
        commands.app,
        [
            "value",
            "missing",
            "--limit",
            "7",
            "--stale-days",
            "45",
            "--with-value",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert captured == {"limit": 7, "stale_days": 45, "with_value": True}


def test_value_missing_csv_json_output(monkeypatch):
    captured: dict[str, object] = {}
    expected_rows = [{"discogs_release_id": 12, "market_need_reason": "missing"}]

    def _run_market_value_missing(
        *, limit: int, stale_days: int | None, with_value: bool
    ):
        captured["limit"] = limit
        captured["stale_days"] = stale_days
        captured["with_value"] = with_value
        return expected_rows

    def _write_market_value_missing_csv(
        *, releases: list[dict[str, object]], output_path: str
    ):
        captured["csv_releases"] = releases
        captured["csv_output_path"] = output_path
        return {"ok": True, "output_path": output_path, "row_count": len(releases)}

    monkeypatch.setattr(commands, "run_market_value_missing", _run_market_value_missing)
    monkeypatch.setattr(
        commands, "write_market_value_missing_csv", _write_market_value_missing_csv
    )
    result = runner.invoke(
        commands.app,
        [
            "value",
            "missing",
            "--limit",
            "6",
            "--stale-days",
            "20",
            "--csv",
            "/tmp/missing.csv",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert captured["with_value"] is True
    assert captured["csv_output_path"] == "/tmp/missing.csv"
    payload = json.loads(result.output)
    assert payload["csv_output_path"] == "/tmp/missing.csv"
    assert payload["csv_row_count"] == 1
    assert payload["releases"] == expected_rows


def test_value_missing_csv_write_error_exits_4(monkeypatch):
    def _run_market_value_missing(
        *, limit: int, stale_days: int | None, with_value: bool
    ):
        _ = limit
        _ = stale_days
        _ = with_value
        return [{"discogs_release_id": 1, "market_need_reason": "missing"}]

    def _write_market_value_missing_csv(
        *, releases: list[dict[str, object]], output_path: str
    ):
        _ = releases
        _ = output_path
        raise OSError("disk full")

    monkeypatch.setattr(commands, "run_market_value_missing", _run_market_value_missing)
    monkeypatch.setattr(
        commands, "write_market_value_missing_csv", _write_market_value_missing_csv
    )
    result = runner.invoke(
        commands.app, ["value", "missing", "--csv", "/tmp/missing.csv"]
    )

    assert result.exit_code == 4
    assert "Failed to write CSV export" in result.output


def test_value_refresh_missing_discogs_token_exits_3(monkeypatch):
    def _raise_missing_token(**kwargs):
        _ = kwargs
        raise MissingDiscogsTokenError("DISCOGS_TOKEN is not set")

    monkeypatch.setattr(commands, "run_refresh_market_values", _raise_missing_token)
    result = runner.invoke(commands.app, ["value", "refresh"])

    assert result.exit_code == 3
    assert "DISCOGS_TOKEN is not set" in result.output


def test_value_refresh_validation_error_exits_2(monkeypatch):
    def _raise_validation(**kwargs):
        _ = kwargs
        raise ValueError("stale_days must be >= 0")

    monkeypatch.setattr(commands, "run_refresh_market_values", _raise_validation)
    result = runner.invoke(commands.app, ["value", "refresh"])

    assert result.exit_code == 2
    assert "stale_days must be >= 0" in result.output


def test_value_refresh_release_ids_are_forwarded(monkeypatch):
    captured: dict[str, object] = {}

    def _run_refresh_market_values(**kwargs):
        captured.update(kwargs)
        return {
            "ok": True,
            "limit": kwargs["limit"],
            "stale_days": kwargs["stale_days"],
            "stale_before": "2026-01-01T00:00:00+00:00",
            "release_ids_requested": kwargs["release_ids"],
            "from_missing": kwargs["from_missing"],
            "candidate_count": 2,
            "refreshed_count": 2,
            "priced_count": 2,
            "unpriced_count": 0,
            "error_count": 0,
            "updated_release_ids": [11, 22],
            "failed_release_ids": [],
            "skipped_release_ids": [],
            "warnings": [],
            "last_refresh_time": "2026-02-07T00:00:00+00:00",
        }

    monkeypatch.setattr(
        commands, "run_refresh_market_values", _run_refresh_market_values
    )
    result = runner.invoke(
        commands.app,
        [
            "value",
            "refresh",
            "--limit",
            "5",
            "--stale-days",
            "9",
            "--release-id",
            "11",
            "--release-id",
            "22",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert captured["release_ids"] == [11, 22]
    assert captured["from_missing"] is False
    payload = json.loads(result.output)
    assert payload["release_ids_requested"] == [11, 22]
    assert payload["candidate_count"] == 2


def test_value_refresh_from_missing_is_forwarded(monkeypatch):
    captured: dict[str, object] = {}

    def _run_refresh_market_values(**kwargs):
        captured.update(kwargs)
        return {
            "ok": True,
            "limit": kwargs["limit"],
            "stale_days": kwargs["stale_days"],
            "stale_before": "2026-01-01T00:00:00+00:00",
            "release_ids_requested": kwargs["release_ids"],
            "from_missing": kwargs["from_missing"],
            "candidate_count": 3,
            "refreshed_count": 3,
            "priced_count": 3,
            "unpriced_count": 0,
            "error_count": 0,
            "updated_release_ids": [1, 2, 3],
            "failed_release_ids": [],
            "skipped_release_ids": [],
            "warnings": [],
            "last_refresh_time": "2026-02-07T00:00:00+00:00",
        }

    monkeypatch.setattr(
        commands, "run_refresh_market_values", _run_refresh_market_values
    )
    result = runner.invoke(
        commands.app,
        [
            "value",
            "refresh",
            "--limit",
            "8",
            "--stale-days",
            "45",
            "--from-missing",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert captured["from_missing"] is True
    assert captured["release_ids"] is None
    payload = json.loads(result.output)
    assert payload["from_missing"] is True
    assert payload["candidate_count"] == 3
