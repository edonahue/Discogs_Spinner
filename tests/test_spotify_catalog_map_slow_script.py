from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _script_text(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def test_spotify_catalog_map_slow_script_contains_expected_markers():
    source = _script_text("scripts/spotify_catalog_map_slow.sh")
    for marker in (
        "--bootstrap-input",
        "--bootstrap-format",
        "--batch-limit",
        "--scope",
        "--api-max-retries",
        "--api-backoff-seconds",
        "--api-max-sleep-seconds",
        "--api-jitter-seconds",
        "--api-retry-after-cap-seconds",
        "--apply-safe-matches",
        "--no-apply-safe-matches",
        "--retry-errors",
        "--no-retry-errors",
        "--stop-on-auth-errors",
        "--no-stop-on-auth-errors",
        "--rate-limit-cooldown-seconds",
        "--retry-after-cap-seconds",
        "--rate-limit-hard-stop-seconds",
        "--reset-report",
        "--lock-path",
        "--log-path",
        "--compact-audit-output",
        "--full-audit-output",
        "status --json",
        "match audit",
        "--apply-safe",
        "--compact",
        "--resume",
        "--retry-errors",
        "--progress-log",
        "DP_SPOTIFY_MAP_SCOPE",
        "DP_SPOTIFY_MAP_MAX_RETRIES",
        "DP_SPOTIFY_API_MAX_RETRIES",
        "DP_SPOTIFY_API_BACKOFF_SECONDS",
        "DP_SPOTIFY_API_MAX_SLEEP_SECONDS",
        "DP_SPOTIFY_API_JITTER_SECONDS",
        "DP_SPOTIFY_API_RETRY_AFTER_CAP_SECONDS",
        "DP_SPOTIFY_MAP_APPLY_SAFE_MATCHES",
        "DP_SPOTIFY_MAP_RETRY_ERRORS",
        "DP_SPOTIFY_MAP_STOP_ON_AUTH_ERRORS",
        "DP_SPOTIFY_MAP_RATE_LIMIT_COOLDOWN_SECONDS",
        "DP_SPOTIFY_MAP_RETRY_AFTER_CAP_SECONDS",
        "DP_SPOTIFY_MAP_RATE_LIMIT_HARD_STOP_SECONDS",
        "DP_SPOTIFY_MAP_RESET_REPORT",
        "DP_SPOTIFY_MAP_LOCK_PATH",
        "DP_SPOTIFY_MAP_LOG_PATH",
        "DP_SPOTIFY_MAP_AUDIT_COMPACT_OUTPUT",
        "spotify_match_audit_slow.json",
        "spotify api retry profile",
        "safe auto-apply during audit",
        "flock -n 9",
        "release_row",
        "retry_after_seconds",
        "header_retry_after_seconds",
        "run_retry_after_max_seconds",
        "run_header_retry_after_max_seconds",
        "rate_limit_signal_seconds",
        "retry-after aware cooldown selected",
        "unmatched_count",
    ):
        assert marker in source
    assert '\\"none\\"' not in source


def test_spotify_catalog_map_slow_script_fails_cleanly_when_not_configured(tmp_path):
    script_path = ROOT / "scripts" / "spotify_catalog_map_slow.sh"
    if not script_path.exists():
        return

    env = os.environ.copy()
    env["PYTHON_BIN"] = sys.executable
    env["XDG_DATA_HOME"] = str(tmp_path / "xdg_data")
    env["XDG_CONFIG_HOME"] = str(tmp_path / "xdg_config")
    env["XDG_CACHE_HOME"] = str(tmp_path / "xdg_cache")
    log_path = tmp_path / "spotify_catalog_map_slow.log"
    env["DP_SPOTIFY_MAP_LOG_PATH"] = str(log_path)
    env["DP_SPOTIFY_MAP_LOCK_PATH"] = str(tmp_path / "spotify_catalog_map_slow.lock")
    env["DP_SPOTIFY_MAP_MAX_BATCHES"] = "1"

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
    assert completed.returncode in {0, 1, 3}
    if completed.returncode == 0:
        assert "spotify catalog mapping complete" in output or "max batch limit reached" in output
    elif completed.returncode == 1:
        assert "Spotify addon unavailable" in output
    else:
        assert "Spotify is not configured" in output

    assert log_path.exists()
    log_text = log_path.read_text(encoding="utf-8")
    assert "spotify catalog mapping worker: checking status" in log_text
    assert "status-check: starting" in log_text
