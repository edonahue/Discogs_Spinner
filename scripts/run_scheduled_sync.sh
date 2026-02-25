#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
STATE_ROOT="${XDG_STATE_HOME:-$HOME/.local/state}"
LOG_PATH="${DP_SYNC_LOG_PATH:-${STATE_ROOT}/discogs_player/sync.log}"
TRACKLIST_WEEKLY_ENABLED="${DP_SYNC_TRACKLIST_WEEKLY_ENABLED:-1}"
TRACKLIST_STALE_DAYS="${DP_SYNC_TRACKLIST_STALE_DAYS:-7}"
TRACKLIST_LIMIT="${DP_SYNC_TRACKLIST_LIMIT:-10000}"
TRACKLIST_WEEK_MARKER_PATH="${DP_SYNC_TRACKLIST_WEEK_MARKER_PATH:-${STATE_ROOT}/discogs_player/tracklist_refresh_week.txt}"

mkdir -p "$(dirname "${LOG_PATH}")"
mkdir -p "$(dirname "${TRACKLIST_WEEK_MARKER_PATH}")"

if [ -x "${REPO_ROOT}/.venv/bin/python" ]; then
  PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3)"
else
  echo "python3 was not found; cannot run scheduled sync" >> "${LOG_PATH}"
  exit 1
fi

export PYTHONPATH="${REPO_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"

run_weekly_tracklist_refresh() {
  if [ "${TRACKLIST_WEEKLY_ENABLED}" = "0" ]; then
    printf '[%s] weekly tracklist refresh disabled\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    return 0
  fi

  local current_week
  current_week="$(date -u +%G-W%V)"
  local previous_week=""
  if [ -f "${TRACKLIST_WEEK_MARKER_PATH}" ]; then
    previous_week="$(tr -d '\n' < "${TRACKLIST_WEEK_MARKER_PATH}" || true)"
  fi

  if [ "${current_week}" = "${previous_week}" ]; then
    printf '[%s] weekly tracklist refresh already completed for %s\n' \
      "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${current_week}"
    return 0
  fi

  printf '[%s] weekly tracklist refresh start (week=%s, stale_days=%s, limit=%s)\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${current_week}" "${TRACKLIST_STALE_DAYS}" "${TRACKLIST_LIMIT}"

  if "${PYTHON_BIN}" -m discogs_player.main tracks refresh \
    --stale-days "${TRACKLIST_STALE_DAYS}" \
    --limit "${TRACKLIST_LIMIT}" \
    --json; then
    printf '%s\n' "${current_week}" > "${TRACKLIST_WEEK_MARKER_PATH}"
    printf '[%s] weekly tracklist refresh success (week=%s)\n' \
      "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${current_week}"
    return 0
  fi

  local exit_code="$?"
  printf '[%s] weekly tracklist refresh failed exit_code=%s\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${exit_code}"
  return "${exit_code}"
}

{
  printf '[%s] scheduled sync start\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  if "${PYTHON_BIN}" -m discogs_player.main sync --no-images; then
    printf '[%s] scheduled sync success\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    if ! run_weekly_tracklist_refresh; then
      printf '[%s] continuing after weekly tracklist refresh failure\n' \
        "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    fi
  else
    exit_code="$?"
    printf '[%s] scheduled sync failed exit_code=%s\n' \
      "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${exit_code}"
    exit "${exit_code}"
  fi
} >> "${LOG_PATH}" 2>&1
