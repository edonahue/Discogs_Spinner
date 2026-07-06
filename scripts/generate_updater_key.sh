#!/usr/bin/env bash
# Generate the Tauri updater key pair for Spinner for Discogs.
#
# Run this ONCE, locally, before the first signed release. The public key
# goes into tauri.conf.json; the private key and passphrase go into GitHub
# repository secrets.
#
# Prerequisites: cargo and tauri-cli must be installed.
#   cargo install tauri-cli --version "^2" --locked
#
# Usage:
#   bash scripts/generate_updater_key.sh
#
# Output:
#   ~/.tauri/discogs_spinner.key        — private key (KEEP SECRET)
#   Printed to stdout:
#     Public key  → paste into desktop_shell/src-tauri/tauri.conf.json
#     Private key → add as GitHub secret TAURI_SIGNING_PRIVATE_KEY
#     Passphrase  → add as GitHub secret TAURI_SIGNING_PRIVATE_KEY_PASSWORD

set -euo pipefail

KEY_PATH="$HOME/.tauri/discogs_spinner.key"

if [[ -f "$KEY_PATH" ]]; then
  echo "Key already exists at $KEY_PATH"
  echo "Delete it first if you want to regenerate: rm $KEY_PATH"
  exit 1
fi

mkdir -p "$HOME/.tauri"

echo "Generating Tauri updater key pair…"
cargo tauri signer generate -w "$KEY_PATH"

echo ""
echo "========================================"
echo " NEXT STEPS"
echo "========================================"
echo ""
echo "1. Copy the PUBLIC KEY printed above into:"
echo "   desktop_shell/src-tauri/tauri.conf.json"
echo "   Replace the value of plugins.updater.pubkey"
echo ""
echo "2. Add the PRIVATE KEY (contents of $KEY_PATH) as:"
echo "   GitHub secret: TAURI_SIGNING_PRIVATE_KEY"
echo "   Settings → Secrets and variables → Actions → New repository secret"
echo ""
echo "3. Add the PASSPHRASE you entered as:"
echo "   GitHub secret: TAURI_SIGNING_PRIVATE_KEY_PASSWORD"
echo ""
echo "After those secrets are set, every tag release will:"
echo "  - Sign all installers (.sig files)"
echo "  - Generate latest.json for in-app update checks"
echo ""
