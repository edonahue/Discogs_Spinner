#!/usr/bin/env bash
# validate_tauri_linux_bundle.sh — verify Linux Tauri bundle outputs and sidecar presence.
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
DEB_FILE="$(ls -t "${BUNDLE_ROOT}"/deb/*.deb 2>/dev/null | head -1 || true)"
APPIMAGE_FILE="$(ls -t "${BUNDLE_ROOT}"/appimage/*.AppImage 2>/dev/null | head -1 || true)"
SOURCE_SIDECAR_NAME="dplayer-api-${TARGET_TRIPLE}"
PACKAGED_SIDECAR_NAME="dplayer-api"

if [[ -z "$DEB_FILE" ]]; then
    echo "ERROR: No Linux .deb bundle found under ${BUNDLE_ROOT}/deb." >&2
    exit 1
fi
if [[ -z "$APPIMAGE_FILE" ]]; then
    echo "ERROR: No Linux AppImage bundle found under ${BUNDLE_ROOT}/appimage." >&2
    exit 1
fi

if ! dpkg-deb -c "$DEB_FILE" | grep -F "usr/bin/${PACKAGED_SIDECAR_NAME}" >/dev/null 2>&1; then
    echo "ERROR: ${DEB_FILE} does not appear to include usr/bin/${PACKAGED_SIDECAR_NAME}." >&2
    exit 1
fi

TMP_DIR="$(mktemp -d)"
cleanup() {
    rm -rf "$TMP_DIR"
}
trap cleanup EXIT

chmod +x "$APPIMAGE_FILE"
(
    cd "$TMP_DIR"
    "$APPIMAGE_FILE" --appimage-extract >/dev/null
)

if ! find "${TMP_DIR}/squashfs-root" -type f \( -name "${PACKAGED_SIDECAR_NAME}" -o -name "${SOURCE_SIDECAR_NAME}" \) | grep -q .; then
    echo "ERROR: ${APPIMAGE_FILE} does not appear to include ${PACKAGED_SIDECAR_NAME} or ${SOURCE_SIDECAR_NAME}." >&2
    exit 1
fi

echo "PASS: Linux Tauri bundles include ${PACKAGED_SIDECAR_NAME}."
