#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "prepublish hygiene: scanning tracked files..."

tracked_bad_files="$(git ls-files | grep -E '(^|/)\.env$|\.db$|^exports/|\.log$' || true)"
if [[ -n "$tracked_bad_files" ]]; then
  echo "FAIL: tracked files violate hygiene policy:"
  echo "$tracked_bad_files"
  exit 1
fi

required_files=(
  "LICENSE"
  "PRIVACY.md"
  "TERMS.md"
  "TRADEMARKS.md"
  "COMPLIANCE.md"
  "docs/STRATEGIC_EXPANSION_NOTES_2026-02-26.md"
  "docs/RELEASE_CHECKLIST_WINDOWS_DEBIAN_MACOS.md"
)

echo "prepublish hygiene: verifying required policy/release docs..."
for path in "${required_files[@]}"; do
  if [[ ! -f "$path" ]]; then
    echo "FAIL: missing required file: $path"
    exit 1
  fi
done

echo "prepublish hygiene: checking .gitignore baseline..."
for marker in ".env" "*.db" "exports/" "*.log"; do
  if ! grep -Fxq "$marker" .gitignore; then
    echo "FAIL: missing .gitignore marker: $marker"
    exit 1
  fi
done

echo "prepublish hygiene: PASS"
