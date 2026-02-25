
from __future__ import annotations

import json

from typer.testing import CliRunner

from discogs_player.cli.commands import app
from discogs_player.data.db import get_connection
from discogs_player.data.repo import upsert_wantlist_entries

runner = CliRunner()


def _wantlist_entry(release_id: int, artist: str = "Artist", title: str = "Title", year: int = 2000):
    return {
        "discogs_release_id": release_id,
        "artist": artist,
        "title": title,
        "year": year,
        "is_active": 1,
    }


def test_wantlist_spin_cli_no_results(isolated_xdg):
    result = runner.invoke(app, ["wantlist", "spin", "--json"])
    assert result.exit_code == 0
    assert "No wantlist items found" in result.stdout


def test_wantlist_spin_cli_with_results(isolated_xdg):
    conn = get_connection()
    try:
        upsert_wantlist_entries(conn, [_wantlist_entry(101)])
    finally:
        conn.close()

    result = runner.invoke(app, ["wantlist", "spin", "--seed", "42", "--json"])
    assert result.exit_code == 0
    assert '"discogs_release_id": 101' in result.stdout


def test_wantlist_spin_cli_invalid_year_exits_2(isolated_xdg):
    result = runner.invoke(app, ["wantlist", "spin", "--year", "2022:2020"])
    assert result.exit_code == 2
    assert "Year range must be start:end with start <= end" in result.stdout


def test_wantlist_spin_cli_forwards_empty_filters(isolated_xdg, monkeypatch):
    captured: dict[str, object] = {}

    def _run_spin_wantlist(**kwargs):
        captured.update(kwargs)
        return {
            "discogs_release_id": 999,
            "artist": "A",
            "title": "B",
            "year": 2001,
        }

    monkeypatch.setattr("discogs_player.use_cases.spin_wantlist.run_spin_wantlist", _run_spin_wantlist)
    result = runner.invoke(app, ["wantlist", "spin", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.stdout)["discogs_release_id"] == 999
    assert captured["genres"] == []
    assert captured["styles"] == []
    assert captured["year"] is None
    assert captured["seed"] is None
