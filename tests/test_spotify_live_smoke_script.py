from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _script_text(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def test_spotify_live_smoke_script_includes_auth_devices_and_play_checks():
    source = _script_text("scripts/spotify_live_smoke.sh")
    for marker in (
        "--auth",
        "--release-id",
        "SPOTIFY_SMOKE_RELEASE_ID",
        "status --json",
        "auth spotify",
        "devices --json",
        "play \"$RELEASE_ID\" --open --json",
        "list --limit 1 --json",
        "fallback_open_url",
        "\"ok\": True",
    ):
        assert marker in source


def test_spotify_live_smoke_script_fails_cleanly_when_auth_not_ready(tmp_path):
    script_path = ROOT / "scripts" / "spotify_live_smoke.sh"
    if not script_path.exists():
        return

    env = os.environ.copy()
    env["PYTHON_BIN"] = sys.executable
    env["XDG_DATA_HOME"] = str(tmp_path / "xdg_data")
    env["XDG_CONFIG_HOME"] = str(tmp_path / "xdg_config")

    completed = subprocess.run(
        ["bash", str(script_path)],
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
        timeout=90,
        check=False,
    )

    output = (completed.stdout or "") + (completed.stderr or "")
    assert completed.returncode in {1, 3}
    if completed.returncode == 1:
        assert "Spotify addon unavailable" in output
    else:
        assert (
            "Spotify is not configured" in output
            or "Spotify auth failed" in output
            or "devices command failed" in output
        )
