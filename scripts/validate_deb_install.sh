#!/usr/bin/env bash
# validate_deb_install.sh — Build the GTK4 .deb and verify a clean install
#                           in a Docker container.
#
# Usage:
#   ./scripts/validate_deb_install.sh
#
# Requires: docker, scripts/build_deb.sh, packaging/test/Dockerfile.debian-clean
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# ---------------------------------------------------------------------------
# Build the .deb
# ---------------------------------------------------------------------------
echo "==> Building .deb package..."
./scripts/build_deb.sh

# ---------------------------------------------------------------------------
# Find the freshly built .deb
# ---------------------------------------------------------------------------
DEB_FILE="$(ls -t dist/installers/*.deb | head -1)"
if [[ -z "$DEB_FILE" ]]; then
    echo "ERROR: No .deb found in dist/installers/ after build." >&2
    exit 1
fi
echo "==> Found package: ${DEB_FILE}"

# Make the path relative to the repo root so COPY works inside Docker build context
DEB_REL="${DEB_FILE#"${ROOT_DIR}/"}"

# ---------------------------------------------------------------------------
# Build Docker image and run install test
# ---------------------------------------------------------------------------
IMAGE_TAG="dplayer-debian-clean-test:local"
echo "==> Building Docker image (${IMAGE_TAG}) with --build-arg DEB_PATH=${DEB_REL}..."
docker build \
    --build-arg "DEB_PATH=${DEB_REL}" \
    -f packaging/test/Dockerfile.debian-clean \
    -t "$IMAGE_TAG" \
    .

echo ""
echo "PASS: Debian clean install — dplayer --version and dplayer-api --help both succeeded."
