#!/usr/bin/env bash
# bump_version.sh — atomically update version strings across all three manifests.
# Usage: ./scripts/bump_version.sh <new-version>   e.g. ./scripts/bump_version.sh 0.3.0

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

NEW_VERSION="${1:-}"

if [[ -z "$NEW_VERSION" ]]; then
    echo "Usage: $0 <new-version>" >&2
    exit 1
fi

# Validate semver (MAJOR.MINOR.PATCH with optional pre-release and build metadata).
if ! [[ "$NEW_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9._-]+)?(\+[a-zA-Z0-9._-]+)?$ ]]; then
    echo "Error: '$NEW_VERSION' is not a valid semver string (expected e.g. 1.2.3 or 1.2.3-alpha.1)." >&2
    exit 1
fi

PYPROJECT="$REPO_ROOT/pyproject.toml"
CARGO="$REPO_ROOT/desktop_shell/src-tauri/Cargo.toml"
PACKAGE_JSON="$REPO_ROOT/webapp/package.json"
SNAPCRAFT="$REPO_ROOT/snap/snapcraft.yaml"

for f in "$PYPROJECT" "$CARGO" "$PACKAGE_JSON" "$SNAPCRAFT"; do
    if [[ ! -f "$f" ]]; then
        echo "Error: expected file not found: $f" >&2
        exit 1
    fi
done

# Read current versions before modifying anything.
CURRENT_PYPROJECT=$(grep -m1 '^version\s*=' "$PYPROJECT" | sed 's/.*= *"\(.*\)".*/\1/')
CURRENT_CARGO=$(grep -m1 '^version\s*=' "$CARGO" | sed 's/.*= *"\(.*\)".*/\1/')
CURRENT_PACKAGE=$(python3 -c "import json, sys; d=json.load(open('$PACKAGE_JSON')); print(d.get('version','?'))")
CURRENT_SNAPCRAFT=$(grep -m1 '^version:' "$SNAPCRAFT" | sed 's/version: *"\(.*\)".*/\1/')

echo "Bumping version: $NEW_VERSION"
echo ""
echo "  pyproject.toml     $CURRENT_PYPROJECT -> $NEW_VERSION"
echo "  Cargo.toml         $CURRENT_CARGO     -> $NEW_VERSION"
echo "  package.json       $CURRENT_PACKAGE   -> $NEW_VERSION"
echo "  snap/snapcraft.yaml $CURRENT_SNAPCRAFT -> $NEW_VERSION"
echo ""

# pyproject.toml: replace first occurrence of version = "..."
sed -i "0,/^version = \"[^\"]*\"/{s/^version = \"[^\"]*\"/version = \"$NEW_VERSION\"/}" "$PYPROJECT"

# Cargo.toml: replace first occurrence of version = "..."
sed -i "0,/^version = \"[^\"]*\"/{s/^version = \"[^\"]*\"/version = \"$NEW_VERSION\"/}" "$CARGO"

# package.json: use python to update "version" key safely
python3 - "$PACKAGE_JSON" "$NEW_VERSION" <<'EOF'
import json, sys

path, new_ver = sys.argv[1], sys.argv[2]
with open(path) as f:
    data = json.load(f)
data["version"] = new_ver
with open(path, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
EOF

# snap/snapcraft.yaml: replace top-level version: "..."
sed -i "s/^version: \"[^\"]*\"/version: \"$NEW_VERSION\"/" "$SNAPCRAFT"

# Verify all four files now report the new version.
VERIFY_PYPROJECT=$(grep -m1 '^version\s*=' "$PYPROJECT" | sed 's/.*= *"\(.*\)".*/\1/')
VERIFY_CARGO=$(grep -m1 '^version\s*=' "$CARGO" | sed 's/.*= *"\(.*\)".*/\1/')
VERIFY_PACKAGE=$(python3 -c "import json; print(json.load(open('$PACKAGE_JSON'))['version'])")
VERIFY_SNAPCRAFT=$(grep -m1 '^version:' "$SNAPCRAFT" | sed 's/version: *"\(.*\)".*/\1/')

FAILED=0
for pair in "pyproject.toml:$VERIFY_PYPROJECT" "Cargo.toml:$VERIFY_CARGO" "package.json:$VERIFY_PACKAGE" "snap/snapcraft.yaml:$VERIFY_SNAPCRAFT"; do
    name="${pair%%:*}"
    ver="${pair##*:}"
    if [[ "$ver" != "$NEW_VERSION" ]]; then
        echo "Error: $name version is '$ver', expected '$NEW_VERSION'" >&2
        FAILED=1
    fi
done

if [[ $FAILED -ne 0 ]]; then
    exit 1
fi

echo "Done. All version files updated to $NEW_VERSION."
