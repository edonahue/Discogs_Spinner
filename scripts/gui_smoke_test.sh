#!/usr/bin/env bash
set -euo pipefail

if ! command -v xvfb-run >/dev/null 2>&1; then
  echo "Missing dependency: xvfb-run" >&2
  echo "Install on Pop!_OS: sudo apt update && sudo apt install -y xvfb" >&2
  exit 1
fi

LIMIT="${1:-12}"

# Improve stability in headless CI/SSH sessions.
export GSK_RENDERER="${GSK_RENDERER:-cairo}"
export LIBGL_ALWAYS_SOFTWARE="${LIBGL_ALWAYS_SOFTWARE:-1}"
if [ -z "${XDG_RUNTIME_DIR:-}" ]; then
  export XDG_RUNTIME_DIR="/tmp/dplayer-runtime-$UID"
  mkdir -p "${XDG_RUNTIME_DIR}"
  chmod 700 "${XDG_RUNTIME_DIR}"
fi

if [ -f ".venv/bin/python" ]; then
  # Prefer venv Python when it can import gi, otherwise fall back to system Python.
  if .venv/bin/python - <<'PY' >/dev/null 2>&1
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
print("ok")
PY
  then
    xvfb-run -a .venv/bin/python -m discogs_player.ui_main --smoke-test --limit "${LIMIT}"
    exit 0
  fi
fi

if [ -x "/usr/bin/python3" ]; then
  SYS_PYTHON="/usr/bin/python3"
elif command -v python3 >/dev/null 2>&1; then
  SYS_PYTHON="$(command -v python3)"
else
  echo "Missing dependency: python3" >&2
  exit 1
fi

# python3-gi from apt is typically available on system Python, not inside venv.
PYTHONPATH=src xvfb-run -a "${SYS_PYTHON}" -m discogs_player.ui_main --smoke-test --limit "${LIMIT}"
