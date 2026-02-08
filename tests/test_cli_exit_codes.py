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
        ["import", "--input", "/tmp/snapshot.json", "--dry-run", "--no-settings", "--json"],
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


def test_wantlist_sync_missing_discogs_token_exits_3(monkeypatch):
    def _raise_missing_token(**kwargs):
        _ = kwargs
        raise MissingDiscogsTokenError("DISCOGS_TOKEN is not set")

    monkeypatch.setattr(commands, "run_sync_wantlist", _raise_missing_token)
    result = runner.invoke(commands.app, ["wantlist", "sync"])

    assert result.exit_code == 3
    assert "DISCOGS_TOKEN is not set" in result.output


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
    expected = [{"discogs_release_id": 777, "artist": "A", "title": "B", "market_median": 12.5}]

    def _run_list_wantlist(**kwargs):
        assert kwargs["with_value"] is True
        return expected

    monkeypatch.setattr(commands, "run_list_wantlist", _run_list_wantlist)
    result = runner.invoke(commands.app, ["wantlist", "list", "--with-value", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.output) == expected


def test_list_with_value_is_forwarded(monkeypatch):
    expected = [{"discogs_release_id": 888, "artist": "A", "title": "B", "market_median": 21.0}]

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
    monkeypatch.setattr(commands, "run_market_value_examples", lambda *, limit: examples)
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

    monkeypatch.setattr(commands, "run_market_value_examples", _run_market_value_examples)
    result = runner.invoke(commands.app, ["value", "examples", "--limit", "2", "--json"])

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
            {"id": 1, "captured_at": "2026-02-07T00:00:00+00:00", "total_median": 125.0},
            {"id": 2, "captured_at": "2026-02-08T00:00:00+00:00", "total_median": 130.0},
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
    result = runner.invoke(commands.app, ["value", "show", "456", "--refresh", "--json"])

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

    def _run_market_value_missing(*, limit: int, stale_days: int | None, with_value: bool):
        assert limit == 5
        assert stale_days is None
        assert with_value is False
        return expected

    monkeypatch.setattr(commands, "run_market_value_missing", _run_market_value_missing)
    result = runner.invoke(commands.app, ["value", "missing", "--limit", "5", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.output) == expected


def test_value_missing_validation_error_exits_2(monkeypatch):
    def _run_market_value_missing(*, limit: int, stale_days: int | None, with_value: bool):
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

    def _run_market_value_missing(*, limit: int, stale_days: int | None, with_value: bool):
        captured["limit"] = limit
        captured["stale_days"] = stale_days
        captured["with_value"] = with_value
        return [{"discogs_release_id": 5, "market_need_reason": "stale"}]

    monkeypatch.setattr(commands, "run_market_value_missing", _run_market_value_missing)
    result = runner.invoke(
        commands.app,
        ["value", "missing", "--limit", "7", "--stale-days", "45", "--with-value", "--json"],
    )

    assert result.exit_code == 0
    assert captured == {"limit": 7, "stale_days": 45, "with_value": True}


def test_value_missing_csv_json_output(monkeypatch):
    captured: dict[str, object] = {}
    expected_rows = [{"discogs_release_id": 12, "market_need_reason": "missing"}]

    def _run_market_value_missing(*, limit: int, stale_days: int | None, with_value: bool):
        captured["limit"] = limit
        captured["stale_days"] = stale_days
        captured["with_value"] = with_value
        return expected_rows

    def _write_market_value_missing_csv(*, releases: list[dict[str, object]], output_path: str):
        captured["csv_releases"] = releases
        captured["csv_output_path"] = output_path
        return {"ok": True, "output_path": output_path, "row_count": len(releases)}

    monkeypatch.setattr(commands, "run_market_value_missing", _run_market_value_missing)
    monkeypatch.setattr(commands, "write_market_value_missing_csv", _write_market_value_missing_csv)
    result = runner.invoke(
        commands.app,
        ["value", "missing", "--limit", "6", "--stale-days", "20", "--csv", "/tmp/missing.csv", "--json"],
    )

    assert result.exit_code == 0
    assert captured["with_value"] is True
    assert captured["csv_output_path"] == "/tmp/missing.csv"
    payload = json.loads(result.output)
    assert payload["csv_output_path"] == "/tmp/missing.csv"
    assert payload["csv_row_count"] == 1
    assert payload["releases"] == expected_rows


def test_value_missing_csv_write_error_exits_4(monkeypatch):
    def _run_market_value_missing(*, limit: int, stale_days: int | None, with_value: bool):
        _ = limit
        _ = stale_days
        _ = with_value
        return [{"discogs_release_id": 1, "market_need_reason": "missing"}]

    def _write_market_value_missing_csv(*, releases: list[dict[str, object]], output_path: str):
        _ = releases
        _ = output_path
        raise OSError("disk full")

    monkeypatch.setattr(commands, "run_market_value_missing", _run_market_value_missing)
    monkeypatch.setattr(commands, "write_market_value_missing_csv", _write_market_value_missing_csv)
    result = runner.invoke(commands.app, ["value", "missing", "--csv", "/tmp/missing.csv"])

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

    monkeypatch.setattr(commands, "run_refresh_market_values", _run_refresh_market_values)
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

    monkeypatch.setattr(commands, "run_refresh_market_values", _run_refresh_market_values)
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
