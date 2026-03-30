#!/usr/bin/env bash
# validate_tauri_macos_bundle.sh — verify macOS Tauri DMG output and sidecar presence.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

TARGET_TRIPLE=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --target-triple)
            TARGET_TRIPLE="$2"
            shift 2
            ;;
        *)
            echo "Unknown argument: $1" >&2
            echo "Usage: $0 --target-triple <triple>" >&2
            exit 2
            ;;
    esac
done

if [[ -z "$TARGET_TRIPLE" ]]; then
    echo "ERROR: --target-triple is required." >&2
    exit 2
fi

BUNDLE_ROOT="${ROOT_DIR}/desktop_shell/src-tauri/target/${TARGET_TRIPLE}/release/bundle"
DMG_FILE="$(ls -t "${BUNDLE_ROOT}"/dmg/*.dmg 2>/dev/null | head -1 || true)"
SOURCE_SIDECAR_NAME="dplayer-api-${TARGET_TRIPLE}"
PACKAGED_SIDECAR_NAME="dplayer-api"

if [[ -z "$DMG_FILE" ]]; then
    echo "ERROR: No macOS .dmg bundle found under ${BUNDLE_ROOT}/dmg." >&2
    exit 1
fi

TMP_DIR="$(mktemp -d)"
MOUNT_DIR="${TMP_DIR}/mount"
mkdir -p "$MOUNT_DIR"

cleanup() {
    hdiutil detach "$MOUNT_DIR" >/dev/null 2>&1 || true
    rm -rf "$TMP_DIR"
}
trap cleanup EXIT

hdiutil attach -nobrowse -readonly -mountpoint "$MOUNT_DIR" "$DMG_FILE" >/dev/null

APP_BUNDLE="$(find "$MOUNT_DIR" -maxdepth 2 -type d -name '*.app' | head -1 || true)"
if [[ -z "$APP_BUNDLE" ]]; then
    echo "ERROR: ${DMG_FILE} does not appear to contain a .app bundle." >&2
    exit 1
fi

MACOS_DIR="${APP_BUNDLE}/Contents/MacOS"
if [[ ! -d "$MACOS_DIR" ]]; then
    echo "ERROR: ${APP_BUNDLE} is missing Contents/MacOS." >&2
    exit 1
fi

if [[ ! -f "${MACOS_DIR}/${PACKAGED_SIDECAR_NAME}" && ! -f "${MACOS_DIR}/${SOURCE_SIDECAR_NAME}" ]]; then
    echo "ERROR: ${DMG_FILE} does not appear to include ${PACKAGED_SIDECAR_NAME} or ${SOURCE_SIDECAR_NAME} in the app bundle." >&2
    exit 1
fi

echo "PASS: macOS Tauri bundle includes ${PACKAGED_SIDECAR_NAME}."
