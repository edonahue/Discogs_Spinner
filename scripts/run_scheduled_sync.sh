#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
STATE_ROOT="${XDG_STATE_HOME:-$HOME/.local/state}"
LOG_PATH="${DP_SYNC_LOG_PATH:-${STATE_ROOT}/discogs_player/sync.log}"

mkdir -p "$(dirname "${LOG_PATH}")"

if [ -x "${REPO_ROOT}/.venv/bin/python" ]; then
  PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3)"
else
  echo "python3 was not found; cannot run scheduled sync" >> "${LOG_PATH}"
  exit 1
fi

export PYTHONPATH="${REPO_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"

{
  printf '[%s] scheduled sync start\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  if "${PYTHON_BIN}" -m discogs_player.main sync --no-images; then
    printf '[%s] scheduled sync success\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  else
    exit_code="$?"
    printf '[%s] scheduled sync failed exit_code=%s\n' \
      "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${exit_code}"
    exit "${exit_code}"
  fi
} >> "${LOG_PATH}" 2>&1
