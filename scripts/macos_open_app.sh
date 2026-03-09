#!/usr/bin/env bash
# macos_open_app.sh — Remove Gatekeeper quarantine and open the app.
#
# Usage:
#   bash scripts/macos_open_app.sh ["/path/to/Discogs Spinner.app"]
#
# Defaults to /Applications/Discogs Spinner.app if no argument is given.
set -euo pipefail

APP="${1:-/Applications/Discogs Spinner.app}"

if [[ ! -d "$APP" ]]; then
    echo "Usage: $0 \"/path/to/Discogs Spinner.app\"" >&2
    echo "App not found: $APP" >&2
    exit 1
fi

echo "Removing Gatekeeper quarantine from: $APP"
xattr -dr com.apple.quarantine "$APP"
echo "Done. You can now open $APP normally."
open "$APP"
