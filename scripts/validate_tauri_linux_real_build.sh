#!/usr/bin/env bash
# validate_tauri_linux_real_build.sh — run the real Linux Tauri bundle build path end to end.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

TARGET_TRIPLE="x86_64-unknown-linux-gnu"
PYTHON_BIN="${PYTHON_BIN:-python3}"
NPM_BIN="${NPM_BIN:-npm}"
RUN_NPM_CI=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --target-triple)
            TARGET_TRIPLE="$2"
            shift 2
            ;;
        --python-bin)
            PYTHON_BIN="$2"
            shift 2
            ;;
        --npm-bin)
            NPM_BIN="$2"
            shift 2
            ;;
        --npm-ci)
            RUN_NPM_CI=1
            shift
            ;;
        *)
            echo "Unknown argument: $1" >&2
            echo "Usage: $0 [--target-triple <triple>] [--python-bin <path>] [--npm-bin <path>] [--npm-ci]" >&2
            exit 2
            ;;
    esac
done

if ! command -v cargo >/dev/null 2>&1; then
    echo "ERROR: cargo is required for the real Tauri bundle build." >&2
    exit 1
fi

if ! command -v "$NPM_BIN" >/dev/null 2>&1; then
    echo "ERROR: npm is required for the webapp build." >&2
    exit 1
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "ERROR: Python binary not found: $PYTHON_BIN" >&2
    exit 1
fi

echo "==> Building Linux sidecar for ${TARGET_TRIPLE}"
PYTHON_BIN="$PYTHON_BIN" ./scripts/build_sidecar.sh --target-triple "$TARGET_TRIPLE"

echo "==> Validating sidecar contract"
python3 ./scripts/validate_tauri_sidecar_contract.py \
    --target-triple "$TARGET_TRIPLE" \
    --require-file \
    --check-executable

echo "==> Building webapp"
(
    cd webapp
    if [[ "$RUN_NPM_CI" -eq 1 ]]; then
        "$NPM_BIN" ci
    fi
    "$NPM_BIN" run build
)

if ! cargo tauri --help >/dev/null 2>&1; then
    echo "==> Installing Tauri CLI"
    cargo install tauri-cli --version "^2" --locked
fi

echo "==> Building Linux Tauri bundles"
(
    cd desktop_shell/src-tauri
    cargo tauri build --target "$TARGET_TRIPLE" --bundles deb,appimage
)

echo "==> Validating Linux bundle contents"
bash ./scripts/validate_tauri_linux_bundle.sh --target-triple "$TARGET_TRIPLE"

echo "PASS: Real Linux Tauri bundle build validation succeeded for ${TARGET_TRIPLE}."
