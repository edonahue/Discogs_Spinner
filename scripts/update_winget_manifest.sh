#!/usr/bin/env bash
# update_winget_manifest.sh — generate WinGet manifests for a new release version.
#
# Usage: ./scripts/update_winget_manifest.sh <new-version>
#   e.g. ./scripts/update_winget_manifest.sh 0.3.0
#
# Requires: curl (for downloading CHECKSUMS-INSTALLERS.txt from the GitHub Release)
#
# What it does:
#   1. Copies the 3 manifest YAMLs from the previous (0.2.2) version directory
#   2. Substitutes the new version string throughout
#   3. Downloads CHECKSUMS-INSTALLERS.txt from the new GitHub Release
#   4. Extracts SHA256 for the .exe (nullsoft) and .msi (wix) installers
#   5. Patches both hashes into the installer YAML
#   6. Prints next steps for the WinGet PR submission

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

NEW_VERSION="${1:-}"

if [[ -z "$NEW_VERSION" ]]; then
    echo "Usage: $0 <new-version>  e.g. $0 0.3.0" >&2
    exit 1
fi

if ! [[ "$NEW_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9._-]+)?$ ]]; then
    echo "Error: '$NEW_VERSION' is not a valid semver string (expected e.g. 1.2.3)." >&2
    exit 1
fi

PUBLISHER="ErichDonahue"
PACKAGE="SpinnerforDiscogs"
IDENTIFIER="${PUBLISHER}.${PACKAGE}"
SOURCE_VERSION="0.2.2"

MANIFESTS_ROOT="${REPO_ROOT}/packaging/winget/manifests/e/${PUBLISHER}/${PACKAGE}"
SOURCE_DIR="${MANIFESTS_ROOT}/${SOURCE_VERSION}"
DEST_DIR="${MANIFESTS_ROOT}/${NEW_VERSION}"

if [[ ! -d "$SOURCE_DIR" ]]; then
    echo "Error: source manifest directory not found: $SOURCE_DIR" >&2
    exit 1
fi

if [[ -d "$DEST_DIR" ]]; then
    echo "Error: destination directory already exists: $DEST_DIR" >&2
    echo "Delete it first if you want to regenerate." >&2
    exit 1
fi

echo "Creating WinGet manifests for ${IDENTIFIER} version ${NEW_VERSION}..."
echo ""

# ── Step 1: copy source manifests ──────────────────────────────────────────
mkdir -p "$DEST_DIR"
for f in "$SOURCE_DIR"/*.yaml; do
    basename_old="$(basename "$f")"
    basename_new="${basename_old/${SOURCE_VERSION}/${NEW_VERSION}}"
    # File names don't contain the version; only contents do — copy as-is for now.
    cp "$f" "${DEST_DIR}/${basename_old}"
done

# ── Step 2: substitute version strings throughout ──────────────────────────
for f in "${DEST_DIR}"/*.yaml; do
    sed -i "s/${SOURCE_VERSION}/${NEW_VERSION}/g" "$f"
done

echo "  ✓ Manifest templates copied and version strings updated."

# ── Step 3: fetch CHECKSUMS-INSTALLERS.txt from the GitHub Release ─────────
CHECKSUMS_URL="https://github.com/edonahue/Discogs_Spinner/releases/download/v${NEW_VERSION}/CHECKSUMS-INSTALLERS.txt"
CHECKSUMS_TMP="$(mktemp)"
trap 'rm -f "$CHECKSUMS_TMP"' EXIT

echo "  Downloading checksums from GitHub Release v${NEW_VERSION}..."
if ! curl -fsSL --retry 3 "$CHECKSUMS_URL" -o "$CHECKSUMS_TMP" 2>/dev/null; then
    # Blank out inherited SHA256 values so stale hashes can't be submitted by accident.
    INSTALLER_YAML="${DEST_DIR}/${IDENTIFIER}.installer.yaml"
    sed -i 's/InstallerSha256: .*/InstallerSha256: PLACEHOLDER_REPLACE_WITH_SHA256_FROM_CHECKSUMS_INSTALLERS_TXT/' "$INSTALLER_YAML"

    echo ""
    echo "  ⚠  Could not download CHECKSUMS-INSTALLERS.txt from:"
    echo "     ${CHECKSUMS_URL}"
    echo ""
    echo "  The release may not exist yet, or the tag name differs."
    echo "  InstallerSha256 fields have been set to PLACEHOLDER — fill them in"
    echo "  from CHECKSUMS-INSTALLERS.txt after the release is published."
    echo "  Manifests were created at: ${DEST_DIR}"
    exit 0
fi

# ── Step 4: extract SHA256 for the .exe and .msi ──────────────────────────
# CHECKSUMS-INSTALLERS.txt format: "<sha256>  <filename>"
EXE_PATTERN="_x64-setup.exe"
MSI_PATTERN="_x64_en-US.msi"

SHA256_EXE="$(awk -v p="$EXE_PATTERN" '$2 ~ p {print $1}' "$CHECKSUMS_TMP")"
SHA256_MSI="$(awk -v p="$MSI_PATTERN" '$2 ~ p {print $1}' "$CHECKSUMS_TMP")"

if [[ -z "$SHA256_EXE" || -z "$SHA256_MSI" ]]; then
    echo ""
    echo "  ⚠  Could not parse SHA256 values from CHECKSUMS-INSTALLERS.txt."
    echo "  File contents:"
    cat "$CHECKSUMS_TMP"
    echo ""
    echo "  Manifests were created at: ${DEST_DIR}"
    echo "  Manually fill in the InstallerSha256 fields before submitting the PR."
    exit 0
fi

echo "  ✓ SHA256 for ${EXE_PATTERN}: ${SHA256_EXE}"
echo "  ✓ SHA256 for ${MSI_PATTERN}: ${SHA256_MSI}"

# ── Step 5: patch hashes into the installer YAML ──────────────────────────
INSTALLER_YAML="${DEST_DIR}/${IDENTIFIER}.installer.yaml"

# Replace InstallerSha256 values in order (exe appears first, msi second).
# Use awk for positional replacement to avoid sed multiline complexity.
awk -v exe_sha="$SHA256_EXE" -v msi_sha="$SHA256_MSI" '
    /InstallerType: nullsoft/ { nullsoft=1 }
    /InstallerType: wix/      { nullsoft=0 }
    /InstallerSha256:/ {
        if (nullsoft) { print "    InstallerSha256: " exe_sha; next }
        else          { print "    InstallerSha256: " msi_sha; next }
    }
    { print }
' "$INSTALLER_YAML" > "${INSTALLER_YAML}.tmp" && mv "${INSTALLER_YAML}.tmp" "$INSTALLER_YAML"

echo "  ✓ Installer SHA256 values patched."
echo ""

# ── Step 6: print next steps ───────────────────────────────────────────────
echo "Done! New manifests:"
for f in "${DEST_DIR}"/*.yaml; do
    echo "  ${f#${REPO_ROOT}/}"
done
echo ""
echo "Next steps:"
echo "  1. Review the manifests in ${DEST_DIR#${REPO_ROOT}/}"
echo "  2. In your microsoft/winget-pkgs fork, create:"
echo "       manifests/e/${PUBLISHER}/${PACKAGE}/${NEW_VERSION}/"
echo "     and copy the 3 YAML files into it."
echo "  3. Open a PR to microsoft/winget-pkgs with title:"
echo "       New package: ${IDENTIFIER} version ${NEW_VERSION}"
echo "  4. Sign the CLA if prompted, then wait for @wingetbot validation."
