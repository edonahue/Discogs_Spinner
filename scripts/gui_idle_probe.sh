#!/usr/bin/env bash
set -euo pipefail

SECONDS_TO_SAMPLE="${1:-10}"
PROFILE="${DP_PERF_PROFILE:-game}"

export DP_PERF_PROFILE="${PROFILE}"
export PYTHONPATH="src${PYTHONPATH:+:${PYTHONPATH}}"
export GSK_RENDERER="${GSK_RENDERER:-cairo}"
export LIBGL_ALWAYS_SOFTWARE="${LIBGL_ALWAYS_SOFTWARE:-1}"
export XDG_RUNTIME_DIR="/tmp/dplayer-runtime-$(id -u)"
mkdir -p "${XDG_RUNTIME_DIR}"
chmod 700 "${XDG_RUNTIME_DIR}" 2>/dev/null || true

has_gtk_bindings() {
  local py_bin="$1"
  "${py_bin}" - <<'PY' >/dev/null 2>&1
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk
PY
}

run_probe() {
  local py_bin="$1"
  if command -v xvfb-run >/dev/null 2>&1; then
    exec xvfb-run -a "${py_bin}" -m discogs_player.ui_main \
      --cover-preload off \
      --idle-probe "${SECONDS_TO_SAMPLE}"
  fi

  exec "${py_bin}" -m discogs_player.ui_main \
    --cover-preload off \
    --idle-probe "${SECONDS_TO_SAMPLE}"
}

if [ -n "${PYTHON_BIN:-}" ] && has_gtk_bindings "${PYTHON_BIN}"; then
  run_probe "${PYTHON_BIN}"
fi

if [ -x ".venv/bin/python" ] && has_gtk_bindings ".venv/bin/python"; then
  run_probe ".venv/bin/python"
fi

if [ -x "/usr/bin/python3" ] && has_gtk_bindings "/usr/bin/python3"; then
  run_probe "/usr/bin/python3"
fi

if command -v python3 >/dev/null 2>&1 && has_gtk_bindings "$(command -v python3)"; then
  run_probe "$(command -v python3)"
fi

echo "No Python runtime with GTK4/libadwaita bindings is available." >&2
exit 1
