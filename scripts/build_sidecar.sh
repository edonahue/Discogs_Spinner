#!/usr/bin/env bash
# build_sidecar.sh — Build the dplayer-api PyInstaller sidecar binary.
#
# The output binary is placed in desktop_shell/src-tauri/binaries/ with
# Tauri's required naming convention:
#   dplayer-api-{rust-target-triple}[.exe]
#
# This script must be run on each target OS (cross-compilation is not
# supported by PyInstaller).
#
# Usage:
#   ./scripts/build_sidecar.sh [--target-triple <triple>]
#
# If --target-triple is omitted the triple is auto-detected from the current
# host OS and architecture.  Override it when building inside a CI matrix:
#   ./scripts/build_sidecar.sh --target-triple x86_64-unknown-linux-gnu
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
TARGET_TRIPLE=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --target-triple)
            TARGET_TRIPLE="$2"
            shift 2
            ;;
        *)
            echo "Unknown argument: $1" >&2
            echo "Usage: $0 [--target-triple <triple>]" >&2
            exit 2
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Auto-detect Rust target triple from host OS + arch
# ---------------------------------------------------------------------------
detect_target_triple() {
    local os arch
    os="$(uname -s 2>/dev/null || echo unknown)"
    arch="$(uname -m 2>/dev/null || echo unknown)"

    case "$os" in
        Linux*)
            case "$arch" in
                x86_64)  echo "x86_64-unknown-linux-gnu" ;;
                aarch64) echo "aarch64-unknown-linux-gnu" ;;
                *)       echo "unknown-unknown-linux-gnu" ;;
            esac
            ;;
        Darwin*)
            case "$arch" in
                x86_64)  echo "x86_64-apple-darwin" ;;
                arm64)   echo "aarch64-apple-darwin" ;;
                *)       echo "unknown-apple-darwin" ;;
            esac
            ;;
        CYGWIN*|MINGW*|MSYS*|Windows_NT)
            case "$arch" in
                x86_64|AMD64) echo "x86_64-pc-windows-msvc" ;;
                aarch64)      echo "aarch64-pc-windows-msvc" ;;
                *)            echo "unknown-pc-windows-msvc" ;;
            esac
            ;;
        *)
            echo "unknown-unknown-unknown-unknown"
            ;;
    esac
}

if [[ -z "$TARGET_TRIPLE" ]]; then
    TARGET_TRIPLE="$(detect_target_triple)"
fi

echo "Building dplayer-api sidecar for target triple: ${TARGET_TRIPLE}"

# ---------------------------------------------------------------------------
# Determine binary name (Windows gets .exe suffix)
# ---------------------------------------------------------------------------
BINARY_NAME="dplayer-api-${TARGET_TRIPLE}"
ADD_DATA_SEPARATOR=":"
SOURCE_DATA_DIR="${ROOT_DIR}/src/discogs_player/data"
case "$TARGET_TRIPLE" in
    *-windows-*)
        BINARY_NAME="${BINARY_NAME}.exe"
        ADD_DATA_SEPARATOR=";"
        if command -v cygpath >/dev/null 2>&1; then
            SOURCE_DATA_DIR="$(cygpath -w "${SOURCE_DATA_DIR}")"
        fi
        ;;
esac

# ---------------------------------------------------------------------------
# Output directory (where Tauri looks for sidecars)
# ---------------------------------------------------------------------------
BINARIES_DIR="${ROOT_DIR}/desktop_shell/src-tauri/binaries"
mkdir -p "$BINARIES_DIR"

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
PYTHON_BIN="${PYTHON_BIN:-python3}"
"$PYTHON_BIN" -m pip install --quiet pyinstaller

echo "Running PyInstaller..."
"$PYTHON_BIN" -m PyInstaller \
    --noconfirm \
    --clean \
    --onefile \
    --name "dplayer-api-${TARGET_TRIPLE}" \
    --distpath "$BINARIES_DIR" \
    --workpath "${ROOT_DIR}/build/pyinstaller_work" \
    --specpath "${ROOT_DIR}/build/pyinstaller_spec" \
    --paths "${ROOT_DIR}/src" \
    --hidden-import uvicorn.logging \
    --hidden-import uvicorn.loops \
    --hidden-import uvicorn.loops.asyncio \
    --hidden-import uvicorn.loops.uvloop \
    --hidden-import uvicorn.protocols \
    --hidden-import uvicorn.protocols.http \
    --hidden-import uvicorn.protocols.http.auto \
    --hidden-import uvicorn.protocols.http.h11_impl \
    --hidden-import uvicorn.protocols.http.httptools_impl \
    --hidden-import uvicorn.protocols.websockets \
    --hidden-import uvicorn.protocols.websockets.auto \
    --hidden-import uvicorn.protocols.websockets.websockets_impl \
    --hidden-import uvicorn.protocols.websockets.wsproto_impl \
    --hidden-import uvicorn.lifespan \
    --hidden-import uvicorn.lifespan.off \
    --hidden-import uvicorn.lifespan.on \
    --hidden-import fastapi \
    --hidden-import starlette \
    --hidden-import starlette.routing \
    --hidden-import starlette.middleware.cors \
    --hidden-import anyio \
    --hidden-import anyio.from_thread \
    --hidden-import discogs_player \
    --hidden-import discogs_player_api \
    --add-data "${SOURCE_DATA_DIR}${ADD_DATA_SEPARATOR}discogs_player/data" \
    --exclude-module gi \
    --exclude-module tkinter \
    --exclude-module PyQt5 \
    --exclude-module PyQt6 \
    "${ROOT_DIR}/src/discogs_player/api_main.py"

echo ""
echo "Sidecar binary written to:"
echo "  ${BINARIES_DIR}/${BINARY_NAME}"
ls -lh "${BINARIES_DIR}/${BINARY_NAME}" || true
