#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

APP_NAME="Discogs Player"
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

has_gtk_bindings() {
  local py_bin="$1"
  "${py_bin}" - <<'PY' >/dev/null 2>&1
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
PY
}

export PYTHONPATH="${REPO_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"

if [ -x "${VENV_PY}" ] && has_gtk_bindings "${VENV_PY}"; then
  exec "${VENV_PY}" -m discogs_player.ui_main "$@"
fi

if command -v python3 >/dev/null 2>&1; then
  SYS_PYTHON="$(command -v python3)"
  if has_gtk_bindings "${SYS_PYTHON}"; then
    exec "${SYS_PYTHON}" -m discogs_player.ui_main "$@"
  fi
fi

echo "GTK4/libadwaita Python bindings are not available." >&2
echo "Install on Pop!_OS with:" >&2
echo "  ${APT_GUI_CMD}" >&2
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
Comment=Browse Discogs collection and control Spotify playback
Exec=${LAUNCHER_PATH}
Icon=${ICON_NAME}
Terminal=false
Categories=AudioVideo;Audio;Player;Music;
Keywords=Discogs;Spotify;Collection;Music;
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
echo "Open your app launcher and search for '${APP_NAME}'."
echo "To add it to your dock, launch it once, then right-click its icon and choose Pin to Dock."
