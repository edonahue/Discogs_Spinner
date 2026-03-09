#!/usr/bin/env bash
# build_deb.sh — Build a .deb installer for the Discogs Spinner GTK4 GUI.
#
# Uses `fpm` (Effing Package Management) to wrap the pip wheel and desktop
# integration files into a Debian package.
#
# Prerequisites on the build host:
#   sudo apt install ruby ruby-dev build-essential
#   sudo gem install fpm
#
# Usage:
#   ./scripts/build_deb.sh [--version <semver>]
#
# Output:
#   dist/installers/discogs-spinner_<version>_amd64.deb
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
PACKAGE_VERSION=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --version)
            PACKAGE_VERSION="$2"
            shift 2
            ;;
        *)
            echo "Unknown argument: $1" >&2
            echo "Usage: $0 [--version <semver>]" >&2
            exit 2
            ;;
    esac
done

# Auto-detect version from pyproject.toml if not provided.
if [[ -z "$PACKAGE_VERSION" ]]; then
    PACKAGE_VERSION="$(python3 -c \
        "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); print(d['project']['version'])" \
        2>/dev/null || echo "0.0.0")"
fi

echo "Building .deb for Discogs Spinner v${PACKAGE_VERSION}"

# ---------------------------------------------------------------------------
# Verify fpm is available
# ---------------------------------------------------------------------------
if ! command -v fpm >/dev/null 2>&1; then
    echo "ERROR: fpm not found. Install with:" >&2
    echo "  sudo apt install ruby ruby-dev build-essential" >&2
    echo "  sudo gem install fpm" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
STAGING_DIR="${ROOT_DIR}/build/deb_staging"
OUTPUT_DIR="${ROOT_DIR}/dist/installers"
INSTALL_PREFIX="/opt/discogs-spinner"
VENV_PATH="${INSTALL_PREFIX}/venv"
DESKTOP_FILE="${ROOT_DIR}/packaging/deb/dplayer-gui.desktop"
POSTINST_SCRIPT="${ROOT_DIR}/packaging/deb/postinst"
ICON_SOURCE="${ROOT_DIR}/assets/icons/discogs-player.svg"

mkdir -p "$STAGING_DIR" "$OUTPUT_DIR"
rm -rf "${STAGING_DIR:?}"/*

# ---------------------------------------------------------------------------
# Build staging tree
# ---------------------------------------------------------------------------

# /usr/bin launcher (calls into the venv Python)
BIN_DIR="${STAGING_DIR}/usr/bin"
mkdir -p "$BIN_DIR"
cat >"${BIN_DIR}/dplayer-gui" <<'SH'
#!/bin/bash
exec /opt/discogs-spinner/venv/bin/python -m discogs_player.ui_main "$@"
SH
chmod 0755 "${BIN_DIR}/dplayer-gui"

# .desktop file
APPS_DIR="${STAGING_DIR}/usr/share/applications"
mkdir -p "$APPS_DIR"
cp "$DESKTOP_FILE" "${APPS_DIR}/discogs-spinner.desktop"

# Icon
ICON_DIR="${STAGING_DIR}/usr/share/icons/hicolor/scalable/apps"
mkdir -p "$ICON_DIR"
if [[ -f "$ICON_SOURCE" ]]; then
    cp "$ICON_SOURCE" "${ICON_DIR}/discogs-spinner.svg"
else
    echo "Warning: icon not found at ${ICON_SOURCE}" >&2
fi

# ---------------------------------------------------------------------------
# Run fpm
# ---------------------------------------------------------------------------
ARCH="$(dpkg --print-architecture 2>/dev/null || echo amd64)"
OUTPUT_DEB="${OUTPUT_DIR}/discogs-spinner_${PACKAGE_VERSION}_${ARCH}.deb"

fpm \
    --input-type dir \
    --output-type deb \
    --name discogs-spinner \
    --version "$PACKAGE_VERSION" \
    --architecture "$ARCH" \
    --maintainer "Discogs Spinner Contributors" \
    --description "Browse your Discogs collection and control Spotify/YouTube Music playback." \
    --url "https://github.com/edonahue/Discogs_Spinner" \
    --license MIT \
    --category "sound" \
    --depends python3 \
    --depends python3-venv \
    --depends python3-gi \
    --depends "gir1.2-gtk-4.0" \
    --depends "gir1.2-adw-1" \
    --depends libadwaita-1-0 \
    --depends "gir1.2-gdkpixbuf-2.0" \
    --after-install "$POSTINST_SCRIPT" \
    --package "$OUTPUT_DEB" \
    --force \
    --chdir "$STAGING_DIR" \
    .

echo ""
echo "Package written to:"
echo "  ${OUTPUT_DEB}"
ls -lh "$OUTPUT_DEB" || true
