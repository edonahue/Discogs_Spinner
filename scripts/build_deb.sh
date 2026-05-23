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
#   PYTHON_BIN=/usr/bin/python3.10 ./scripts/build_deb.sh
#
# Output:
#   dist/installers/discogs-spinner_<version>_amd64.deb
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
PYTHON_BIN="${PYTHON_BIN:-}"

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
    PACKAGE_VERSION="$(
        awk -F'"' '
            $0 == "[project]" { in_project = 1; next }
            /^\[/ && $0 != "[project]" { in_project = 0 }
            in_project && $1 ~ /^version = / { print $2; exit }
        ' pyproject.toml
    )"
    if [[ -z "$PACKAGE_VERSION" ]]; then
        PACKAGE_VERSION="0.0.0"
    fi
fi

echo "Building .deb for Discogs Spinner v${PACKAGE_VERSION}"

# ---------------------------------------------------------------------------
# Resolve Python build interpreter
# ---------------------------------------------------------------------------
if [[ -n "$PYTHON_BIN" ]]; then
    if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
        echo "ERROR: Python executable not found: ${PYTHON_BIN}" >&2
        exit 1
    fi
else
    for candidate in python3.10 python3; do
        if command -v "$candidate" >/dev/null 2>&1 \
            && "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 10) else 1)' >/dev/null 2>&1; then
            PYTHON_BIN="$candidate"
            break
        fi
    done
fi

if [[ -z "$PYTHON_BIN" ]] || ! "$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 10) else 1)' >/dev/null 2>&1; then
    echo "ERROR: build_deb.sh must build the wheelhouse with Python 3.10 to match the Debian runtime." >&2
    echo "Set PYTHON_BIN to a Python 3.10 interpreter, for example:" >&2
    echo "  PYTHON_BIN=/usr/bin/python3.10 ./scripts/build_deb.sh" >&2
    exit 1
fi

PYTHON_VERSION="$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")')"
echo "Using build interpreter: ${PYTHON_BIN} (${PYTHON_VERSION})"

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
WHEEL_DIR="${STAGING_DIR}${INSTALL_PREFIX}/wheels"
DESKTOP_FILE="${ROOT_DIR}/packaging/deb/dplayer-gui.desktop"
METAINFO_FILE="${ROOT_DIR}/packaging/deb/io.github.edonahue.DiscogsSpinner.metainfo.xml"
POSTINST_SCRIPT="${ROOT_DIR}/packaging/deb/postinst"
ICON_SOURCE="${ROOT_DIR}/assets/icons/discogs-player.svg"

mkdir -p "$STAGING_DIR" "$OUTPUT_DIR"
rm -rf "${STAGING_DIR:?}"/*

# ---------------------------------------------------------------------------
# Build staging tree
# ---------------------------------------------------------------------------

# Bundle an offline wheelhouse for postinst, including the web profile so the
# installed dplayer-api entrypoint works without network access.
mkdir -p "$WHEEL_DIR"
"$PYTHON_BIN" -m pip wheel --wheel-dir "$WHEEL_DIR" '.[web]'

# /usr/bin launchers (call into the venv Python)
BIN_DIR="${STAGING_DIR}/usr/bin"
mkdir -p "$BIN_DIR"

cat >"${BIN_DIR}/dplayer" <<'SH'
#!/bin/bash
exec /opt/discogs-spinner/venv/bin/python -m discogs_player.main "$@"
SH
chmod 0755 "${BIN_DIR}/dplayer"

cat >"${BIN_DIR}/dplayer-api" <<'SH'
#!/bin/bash
exec /opt/discogs-spinner/venv/bin/python -m discogs_player.api_main "$@"
SH
chmod 0755 "${BIN_DIR}/dplayer-api"

cat >"${BIN_DIR}/dplayer-gui" <<'SH'
#!/bin/bash
export DP_PERF_PROFILE="${DP_PERF_PROFILE:-quiet}"
exec /opt/discogs-spinner/venv/bin/python -m discogs_player.ui_main "$@"
SH
chmod 0755 "${BIN_DIR}/dplayer-gui"

# .desktop file
APPS_DIR="${STAGING_DIR}/usr/share/applications"
mkdir -p "$APPS_DIR"
cp "$DESKTOP_FILE" "${APPS_DIR}/discogs-spinner.desktop"

# AppStream metadata for software-center style package listings.
METAINFO_DIR="${STAGING_DIR}/usr/share/metainfo"
mkdir -p "$METAINFO_DIR"
cp "$METAINFO_FILE" "${METAINFO_DIR}/io.github.edonahue.DiscogsSpinner.metainfo.xml"

# Icon
ICON_DIR="${STAGING_DIR}/usr/share/icons/hicolor/scalable/apps"
mkdir -p "$ICON_DIR"
if [[ -f "$ICON_SOURCE" ]]; then
    cp "$ICON_SOURCE" "${ICON_DIR}/discogs-spinner.svg"
else
    echo "Warning: icon not found at ${ICON_SOURCE}" >&2
fi

# Debian package metadata.
DOC_DIR="${STAGING_DIR}/usr/share/doc/discogs-spinner"
mkdir -p "$DOC_DIR"
cp "${ROOT_DIR}/LICENSE" "${DOC_DIR}/copyright"

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
    --maintainer "Discogs Spinner Contributors <discogs_player+maintainer@users.noreply.github.com>" \
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
