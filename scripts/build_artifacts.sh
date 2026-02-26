#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-all}"
if [[ "$TARGET" != "all" && "$TARGET" != "core" && "$TARGET" != "plus" ]]; then
  echo "Usage: $0 [all|core|plus]" >&2
  exit 2
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
normalize_os_name() {
  local raw="$1"
  case "$raw" in
    Linux*) echo "linux" ;;
    Darwin*) echo "macos" ;;
    CYGWIN*|MINGW*|MSYS*|Windows_NT) echo "windows" ;;
    *) echo "$(printf '%s' "$raw" | tr '[:upper:]' '[:lower:]')" ;;
  esac
}

normalize_arch_name() {
  local raw
  raw="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
  case "$raw" in
    x86_64|amd64) echo "x86_64" ;;
    aarch64|arm64) echo "arm64" ;;
    *) echo "$raw" ;;
  esac
}

RAW_OS_NAME="$(uname -s 2>/dev/null || echo unknown)"
RAW_ARCH_NAME="$(uname -m 2>/dev/null || echo unknown)"
OS_NAME="${OS_NAME_OVERRIDE:-$(normalize_os_name "$RAW_OS_NAME")}"
ARCH_NAME="${ARCH_NAME_OVERRIDE:-$(normalize_arch_name "$RAW_ARCH_NAME")}"
PLATFORM_TAG="${OS_NAME}-${ARCH_NAME}"
ARTIFACT_DIR="dist/artifacts/${PLATFORM_TAG}"
PIP_NO_BUILD_ISOLATION="${PIP_NO_BUILD_ISOLATION:-0}"
PIP_WHEEL_NO_DEPS="${PIP_WHEEL_NO_DEPS:-0}"

mkdir -p "$ARTIFACT_DIR"

make_temp_dir() {
  local tmp_dir=""
  # GNU mktemp supports `mktemp -d`; BSD/macOS requires `-t` when no template is passed.
  if tmp_dir="$(mktemp -d 2>/dev/null)"; then
    printf '%s\n' "$tmp_dir"
    return 0
  fi
  if tmp_dir="$(mktemp -d -t discogs_player_artifacts 2>/dev/null)"; then
    printf '%s\n' "$tmp_dir"
    return 0
  fi
  echo "Failed to create temporary directory with mktemp." >&2
  return 1
}

build_profile() {
  local profile="$1"
  local requirement="$2"

  local tmp_dir
  tmp_dir="$(make_temp_dir)"

  echo "Building ${profile} wheel bundle for ${PLATFORM_TAG}..."
  local wheel_args=()
  if [[ "$PIP_NO_BUILD_ISOLATION" == "1" ]]; then
    wheel_args+=("--no-build-isolation")
  fi
  if [[ "$PIP_WHEEL_NO_DEPS" == "1" ]]; then
    wheel_args+=("--no-deps")
  fi
  if ((${#wheel_args[@]})); then
    "$PYTHON_BIN" -m pip wheel "${wheel_args[@]}" --wheel-dir "$tmp_dir" "$requirement"
  else
    "$PYTHON_BIN" -m pip wheel --wheel-dir "$tmp_dir" "$requirement"
  fi

  cat >"${tmp_dir}/INSTALL.txt" <<TXT
Profile: ${profile}
Platform: ${PLATFORM_TAG}

Install from source:
  pip install ${requirement}

Install from this artifact directory:
  pip install *.whl

Build options:
  PIP_NO_BUILD_ISOLATION=${PIP_NO_BUILD_ISOLATION}
  PIP_WHEEL_NO_DEPS=${PIP_WHEEL_NO_DEPS}
TXT

  local tarball="${ARTIFACT_DIR}/discogs_player-${profile}-${PLATFORM_TAG}.tar.gz"
  tar -C "$tmp_dir" -czf "$tarball" .
  rm -rf "$tmp_dir"

  echo "Created: ${tarball}"
}

if [[ "$TARGET" == "all" || "$TARGET" == "core" ]]; then
  build_profile "core" "."
fi

if [[ "$TARGET" == "all" || "$TARGET" == "plus" ]]; then
  build_profile "plus" ".[spotify]"
fi
