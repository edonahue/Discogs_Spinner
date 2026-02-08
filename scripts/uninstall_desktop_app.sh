#!/usr/bin/env bash
set -euo pipefail

DESKTOP_ID="discogs-player.desktop"
ICON_NAME="discogs-player"
LAUNCHER_NAME="discogs-player-gui"

XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
INSTALL_BIN_DIR="${INSTALL_BIN_DIR:-$HOME/.local/bin}"
APPLICATIONS_DIR="${XDG_DATA_HOME}/applications"
ICON_PATH="${XDG_DATA_HOME}/icons/hicolor/scalable/apps/${ICON_NAME}.svg"
DESKTOP_PATH="${APPLICATIONS_DIR}/${DESKTOP_ID}"
LAUNCHER_PATH="${INSTALL_BIN_DIR}/${LAUNCHER_NAME}"

rm -f "${DESKTOP_PATH}" "${ICON_PATH}" "${LAUNCHER_PATH}"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "${APPLICATIONS_DIR}" || true
fi

echo "Removed desktop entry: ${DESKTOP_PATH}"
echo "Removed icon:          ${ICON_PATH}"
echo "Removed launcher:      ${LAUNCHER_PATH}"
