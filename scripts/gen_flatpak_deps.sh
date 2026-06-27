#!/usr/bin/env bash
# gen_flatpak_deps.sh — generate the bundled Python dependency sources for the
# Flathub build (python3-deps.json) using flatpak-pip-generator.
#
# Usage: ./scripts/gen_flatpak_deps.sh
#
# Requires: python3 + pip, and flatpak-pip-generator on PATH
#   pip install flatpak-pip-generator
#
# What it does:
#   1. Runs flatpak-pip-generator against the GNOME SDK runtime with the exact
#      runtime dependency set Spinner for Discogs needs at execution time.
#   2. Writes python3-deps.json next to the Flatpak manifest.
#   3. Reminds you to uncomment the "- python3-deps.json" include in the manifest
#      and to commit the generated file alongside it.
#
# Keep the dependency list below in sync with the runtime deps in pyproject.toml.
# (Build-only / dev / test extras are intentionally excluded — Flathub builds the
# app, it does not run the test suite.)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST_DIR="$REPO_ROOT/packaging/flatpak"
OUTPUT="$MANIFEST_DIR/python3-deps.json"

# GNOME SDK version must match runtime-version in the Flatpak manifest.
GNOME_SDK="org.gnome.Sdk//48"

# Runtime dependencies (core + optional Spotify/YouTube Music integrations).
DEPS=(
    httpx
    uvicorn
    fastapi
    starlette
    anyio
    h11
    httpcore
    typer
    rich
    python-dotenv
    ytmusicapi
    platformdirs
    keyring
    rapidfuzz
    certifi
    idna
    sniffio
)

if ! command -v flatpak-pip-generator >/dev/null 2>&1; then
    echo "error: flatpak-pip-generator not found on PATH." >&2
    echo "       Install it with: pip install flatpak-pip-generator" >&2
    exit 1
fi

echo "Generating Flatpak Python deps with runtime $GNOME_SDK ..."
flatpak-pip-generator --runtime "$GNOME_SDK" "${DEPS[@]}" --output "${OUTPUT%.json}"

echo
echo "Wrote: $OUTPUT"
echo
echo "Next steps:"
echo "  1. Uncomment '- python3-deps.json' under 'modules:' in"
echo "     packaging/flatpak/com.discogs-spinner.app.yml"
echo "  2. Commit python3-deps.json alongside the manifest."
echo "  3. See docs/flathub_submission_checklist.md for the remaining steps."
