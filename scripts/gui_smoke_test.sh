#!/usr/bin/env bash
set -euo pipefail

if ! command -v xvfb-run >/dev/null 2>&1; then
  echo "Missing dependency: xvfb-run" >&2
  echo "Install on Pop!_OS: sudo apt update && sudo apt install -y xvfb" >&2
  exit 1
fi

if [ ! -f ".venv/bin/activate" ]; then
  echo "Missing .venv. Create it with: python3 -m venv .venv" >&2
  exit 1
fi

source .venv/bin/activate

LIMIT="${1:-12}"
xvfb-run -a python -m discogs_player.ui_main --smoke-test --limit "${LIMIT}"

