from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _script_text(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def test_spotify_mapping_report_script_contains_expected_markers():
    source = _script_text("scripts/spotify_mapping_report.sh")
    for marker in (
        "--db",
        "--limit",
        "sqlite3 -readonly -header -column",
        "FROM spotify_mapping",
        "mapped_active_releases",
        "unmatched_active_releases",
        "persisted_mappings_total",
        "COALESCE(r.artist, w.artist, 'Unknown')",
    ):
        assert marker in source


def test_spotify_mapping_report_script_fails_cleanly_when_db_missing(tmp_path):
    script_path = ROOT / "scripts" / "spotify_mapping_report.sh"
    if not script_path.exists():
        return

    missing_db = tmp_path / "missing_app.db"
    completed = subprocess.run(
        ["bash", str(script_path), "--db", str(missing_db)],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )

    output = (completed.stdout or "") + (completed.stderr or "")
    assert completed.returncode == 1
    assert (
        "sqlite3 not found." in output
        or f"DB not found: {missing_db}" in output
    )
