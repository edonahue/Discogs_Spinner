#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

APP_NAME="Spinner for Discogs"
DESKTOP_ID="discogs-player.desktop"
ICON_NAME="discogs-player"
LAUNCHER_NAME="discogs-player-gui"

XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
INSTALL_BIN_DIR="${INSTALL_BIN_DIR:-$HOME/.local/bin}"
APPLICATIONS_DIR="${XDG_DATA_HOME}/applications"
ICON_DIR="${XDG_DATA_HOME}/icons/hicolor/scalable/apps"

LAUNCHER_PATH="${INSTALL_BIN_DIR}/${LAUNCHER_NAME}"
DESKTOP_PATH="${APPLICATIONS_DIR}/${DESKTOP_ID}"
ICON_SOURCE="${REPO_ROOT}/assets/icons/${ICON_NAME}.svg"
ICON_TARGET="${ICON_DIR}/${ICON_NAME}.svg"

if [ ! -f "${ICON_SOURCE}" ]; then
  echo "Icon source not found: ${ICON_SOURCE}" >&2
  exit 1
fi

mkdir -p "${INSTALL_BIN_DIR}" "${APPLICATIONS_DIR}" "${ICON_DIR}"

cat > "${LAUNCHER_PATH}" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="__REPO_ROOT__"
VENV_PY="${REPO_ROOT}/.venv/bin/python"
APT_GUI_CMD="sudo apt update && sudo apt install -y python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 libadwaita-1-0 gir1.2-gdkpixbuf-2.0"
XDG_STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}"
LOG_DIR="${XDG_STATE_HOME}/discogs_player"
LOG_PATH="${LOG_DIR}/gui-launch.log"

timestamp() {
  date -Iseconds
}

ensure_log_writable() {
  if [ ! -d "${LOG_DIR}" ]; then
    mkdir -p "${LOG_DIR}" >/dev/null 2>&1 || return 1
  fi
  if [ ! -e "${LOG_PATH}" ]; then
    : >"${LOG_PATH}" 2>/dev/null || return 1
  fi
  [ -w "${LOG_PATH}" ]
}

log_line() {
  local message="$1"
  if ! ensure_log_writable; then
    return 0
  fi
  printf '[%s] %s\n' "$(timestamp)" "${message}" >>"${LOG_PATH}" || true
}

notify_failure() {
  local message="$1"
  if command -v notify-send >/dev/null 2>&1; then
    notify-send "Spinner for Discogs" "${message}" || true
  fi
}

has_gtk_bindings() {
  local py_bin="$1"
  "${py_bin}" - <<'PY' >/dev/null 2>&1
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk
PY
}

export PYTHONPATH="${REPO_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
export DP_PERF_PROFILE="${DP_PERF_PROFILE:-game}"

run_with_python() {
  local py_bin="$1"
  local label="$2"
  shift 2

  if ! has_gtk_bindings "${py_bin}"; then
    log_line "Skipping ${label} runtime (${py_bin}): GTK bindings unavailable"
    return 1
  fi

  log_line "Launching Spinner for Discogs with ${label} runtime (${py_bin})"
  local rc=0
  if ensure_log_writable; then
    if "${py_bin}" -m discogs_player.ui_main "$@" >>"${LOG_PATH}" 2>&1; then
      rc=0
    else
      rc=$?
    fi
  else
    if "${py_bin}" -m discogs_player.ui_main "$@"; then
      rc=0
    else
      rc=$?
    fi
  fi

  if [ "${rc}" -eq 0 ]; then
    log_line "Spinner for Discogs exited cleanly via ${label} runtime"
    return 0
  fi

  log_line "Spinner for Discogs exited with rc=${rc} via ${label} runtime"
  return "${rc}"
}

if [ ! -d "${REPO_ROOT}/src/discogs_player" ]; then
  message="Repository path missing: ${REPO_ROOT}"
  log_line "${message}"
  notify_failure "${message}"
  exit 1
fi

if [ ! -e "${XDG_RUNTIME_DIR}" ]; then
  log_line "Warning: XDG_RUNTIME_DIR does not exist (${XDG_RUNTIME_DIR})"
fi

if [ -x "${VENV_PY}" ] && run_with_python "${VENV_PY}" "venv" "$@"; then
  exit 0
fi

if [ -x "/usr/bin/python3" ]; then
  SYS_PYTHON="/usr/bin/python3"
elif command -v python3 >/dev/null 2>&1; then
  SYS_PYTHON="$(command -v python3)"
else
  SYS_PYTHON=""
fi

if [ -n "${SYS_PYTHON}" ]; then
  if run_with_python "${SYS_PYTHON}" "system" "$@"; then
    exit 0
  fi
fi

echo "Spinner for Discogs launcher failed. See ${LOG_PATH}" >&2
echo "GTK4/libadwaita Python bindings are not available." >&2
echo "Install on Pop!_OS with:" >&2
echo "  ${APT_GUI_CMD}" >&2
notify_failure "Launch failed. Check ${LOG_PATH}"
exit 1
EOF

sed -i "s|__REPO_ROOT__|${REPO_ROOT}|g" "${LAUNCHER_PATH}"
chmod +x "${LAUNCHER_PATH}"

install -m 0644 "${ICON_SOURCE}" "${ICON_TARGET}"

cat > "${DESKTOP_PATH}" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=${APP_NAME}
Comment=Browse, spin, and value your Discogs vinyl collection
Exec=${LAUNCHER_PATH}
Icon=${ICON_NAME}
Terminal=false
Categories=AudioVideo;Audio;Player;Music;
Keywords=Discogs;Records;Vinyl;Collection;Wantlist;Market Value;Spotify;YouTube;Music;
StartupNotify=true
StartupWMClass=com.discogs_player.app
EOF

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "${APPLICATIONS_DIR}" || true
fi

echo "Installed launcher script: ${LAUNCHER_PATH}"
echo "Installed desktop entry:  ${DESKTOP_PATH}"
echo "Installed icon:           ${ICON_TARGET}"
echo
echo "First-time setup for vinyl collectors:"
echo "  1. Get your Discogs personal access token:"
echo "     https://www.discogs.com/settings/developers"
echo "     (Personal Access Tokens → Generate new token)"
echo "  2. Launch Spinner for Discogs and paste the token into the setup wizard."
echo "  3. Sync once, then browse your records and use Spin for a quick pick."
echo
echo "Terminal alternative:"
echo "  Store the token permanently:"
echo "       dplayer config set discogs_token <your_token>"
echo "     or set the environment variable in your shell profile:"
echo "       export DISCOGS_TOKEN=\"your_discogs_token\""
echo
echo "Open your app launcher and search for '${APP_NAME}'."
echo "To add it to your dock, launch it once, then right-click its icon and choose Pin to Dock."
