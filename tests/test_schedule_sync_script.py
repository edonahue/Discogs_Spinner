from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _script_text(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def test_scheduled_sync_script_includes_weekly_tracklist_refresh_hook():
    source = _script_text("scripts/run_scheduled_sync.sh")
    for marker in (
        'TRACKLIST_WEEKLY_ENABLED="${DP_SYNC_TRACKLIST_WEEKLY_ENABLED:-1}"',
        'TRACKLIST_STALE_DAYS="${DP_SYNC_TRACKLIST_STALE_DAYS:-7}"',
        'TRACKLIST_LIMIT="${DP_SYNC_TRACKLIST_LIMIT:-10000}"',
        'TRACKLIST_WEEK_MARKER_PATH="${DP_SYNC_TRACKLIST_WEEK_MARKER_PATH:-${STATE_ROOT}/discogs_player/tracklist_refresh_week.txt}"',
        "run_weekly_tracklist_refresh() {",
        '"${PYTHON_BIN}" -m discogs_player.main tracks refresh',
        '--stale-days "${TRACKLIST_STALE_DAYS}"',
        '--limit "${TRACKLIST_LIMIT}"',
        "weekly tracklist refresh already completed",
        "continuing after weekly tracklist refresh failure",
    ):
        assert marker in source
