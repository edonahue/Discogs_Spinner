# Store Submissions Guide

This document covers the end-to-end submission steps for each official distribution
channel. Complete steps in the order shown — later channels depend on earlier ones.

---

## Naming Convention

All **store display names** use **"Spinner for Discogs"** to comply with Discogs LLC
trademark guidelines and clearly indicate this is an unofficial third-party client.

Internal package identifiers (`discogs-spinner`, `com.discogs-spinner.app`) are
descriptive and do not imply official Discogs affiliation.

---

## Prerequisites (Do These First)

### Apple Developer Program
Required for: macOS notarization, Homebrew Cask submission.
- Enroll at https://developer.apple.com/programs/ ($99/yr)
- In Xcode → Settings → Accounts, create a **Developer ID Application** certificate
- Export it as a `.p12` file from Keychain Access (File → Export Items)
- Base64-encode and add to GitHub Secrets:

```bash
base64 -i certificate.p12 | pbcopy   # macOS — copies to clipboard
```

| Secret name | Value |
|---|---|
| `APPLE_CERTIFICATE` | Base64-encoded `.p12` content |
| `APPLE_CERTIFICATE_PASSWORD` | Password protecting the `.p12` |
| `APPLE_SIGNING_IDENTITY` | Certificate common name, e.g. `Developer ID Application: Eric Donahue (XXXXXXXXXX)` |
| `APPLE_ID` | Your Apple ID email |
| `APPLE_TEAM_ID` | 10-character team ID from developer.apple.com/account |
| `APPLE_APP_SPECIFIC_PASSWORD` | App-specific password from appleid.apple.com → Security |

Once secrets are set, the next CI run on a version tag will produce notarized `.dmg` files.
Verify with: `spctl --assess --verbose /Applications/DiscogSpinner.app`

### Microsoft Partner Center
Required for: Microsoft Store (MSIX) submission.
- Register at https://partner.microsoft.com/dashboard ($19 one-time)
- Reserve the app name **"Spinner for Discogs"**
- On the app overview → **App identity** page, note:
  - **Publisher display name** (as registered)
  - **Package/Identity Name** (e.g. `ErichDonahue.SpinnerforDiscogs` or a GUID-based string)
- Update `desktop_shell/src-tauri/tauri.conf.json` → `bundle.windows.msix`:
  - `identityName` → the exact Package/Identity Name from App identity page
  - `publisherDisplayName` → your registered Publisher Display Name
- Commit and push — CI will build a fresh MSIX with the correct identity on the next tag

---

## Channel 1: Homebrew Cask (macOS)

**Prerequisites:** Apple Developer Program, notarized `.dmg` on latest release.

**File:** `packaging/homebrew/spinner-for-discogs.rb`

1. Download the notarized `.dmg` files for both architectures from the GitHub Release
2. Compute SHA256 checksums and replace the `PLACEHOLDER_SHA256_*` values in the formula
3. Fork https://github.com/Homebrew/homebrew-cask
4. Copy the formula to `Casks/s/spinner-for-discogs.rb`
5. Run locally: `brew install --cask ./Casks/s/spinner-for-discogs.rb`
6. Run: `brew audit --cask --new spinner-for-discogs`
7. Submit PR to homebrew/homebrew-cask

---

## Channel 2: WinGet (Windows Package Manager)

**Prerequisites:** None (no signing required for WinGet).

**Files:** `packaging/winget/manifests/e/ErichDonahue/SpinnerforDiscogs/<VERSION>/`

For new releases, use the automation script (see [Per-Release Checklist](#per-release-checklist)):

```bash
./scripts/update_winget_manifest.sh 0.3.0
```

This downloads `CHECKSUMS-INSTALLERS.txt` from the GitHub Release, fills in the correct
SHA256 values, and creates a ready-to-submit manifest directory.

For manual submission:
1. Fork https://github.com/microsoft/winget-pkgs
2. Copy the new version directory to `manifests/e/ErichDonahue/SpinnerforDiscogs/<VERSION>/`
3. Submit PR — WinGet bot auto-validates manifests within minutes
4. Sign the CLA if prompted (`@microsoft-github-policy-service agree`)
5. Maintainers typically merge within 1-3 days

---

## Channel 3: Flathub (Linux — GTK4 app)

**Prerequisites:** AppStream screenshots (at least 2 at 1248×702 or 624×351).

**Files:** `packaging/flatpak/com.discogs-spinner.app.yml`, `packaging/metainfo/com.discogs-spinner.app.metainfo.xml`

1. Install build tools:
   ```bash
   sudo apt install flatpak flatpak-builder appstream
   pip install flatpak-pip-generator
   ```

2. Generate Python dependency sources (re-run whenever `pyproject.toml` deps change):
   ```bash
   flatpak-pip-generator --runtime org.gnome.Sdk//48 \
     httpx uvicorn fastapi starlette anyio h11 httpcore \
     typer rich python-dotenv ytmusicapi platformdirs \
     keyring rapidfuzz certifi idna sniffio \
     > packaging/flatpak/python3-deps.json
   ```
   Then uncomment the `- python3-deps.json` line in the Flatpak manifest.

3. Add screenshots to `packaging/metainfo/` and uncomment the `<screenshots>` block
   in `packaging/metainfo/com.discogs-spinner.app.metainfo.xml`

4. Validate the metainfo:
   ```bash
   appstreamcli validate packaging/metainfo/com.discogs-spinner.app.metainfo.xml
   ```

5. Test the Flatpak build locally:
   ```bash
   flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
   flatpak install org.gnome.Platform//48 org.gnome.Sdk//48
   flatpak-builder --sandbox --install --force-clean \
     build-dir packaging/flatpak/com.discogs-spinner.app.yml
   flatpak run com.discogs-spinner.app
   ```

6. Update the `commit:` field in the manifest to the exact git commit SHA of the release tag

7. Fork https://github.com/flathub/flathub and submit a PR with:
   - `com.discogs-spinner.app.yml`
   - `python3-deps.json`
   - Screenshots in `screenshots/` subdirectory

Flathub review typically takes 1-4 weeks.

---

## Channel 4: Snap Store (Linux)

**Prerequisites:** None (free Snapcraft account).

**File:** `snap/snapcraft.yaml`

**Recommended: GitHub-connected build service (no local tooling needed)**

1. Create account at https://snapcraft.io/create-account
2. Register snap name: snapcraft.io → My snaps → **New snap** → name: `spinner-for-discogs`
3. In snap dashboard → **Builds** → "Connect a GitHub repo" →
   repo: `edonahue/Discogs_Spinner`, manifest path: `snap/snapcraft.yaml`
4. Click **Request build** — Snap Store builds and publishes to the `stable` track automatically
5. Future versions: updating `version:` in `snapcraft.yaml` as part of the release commit
   auto-triggers a rebuild (no manual upload needed)

**Alternative: local build and upload**
```bash
sudo snap install snapcraft --classic
snapcraft login
# from repo root:
snapcraft --destructive-mode
snapcraft upload spinner-for-discogs_0.2.2_amd64.snap --release=stable
```

---

## Channel 5: Microsoft Store (MSIX)

**Prerequisites:** Microsoft Partner Center account, Publisher Display Name configured in `tauri.conf.json`.

The MSIX artifact is now built automatically by the CI on every tagged release. After
a tag push completes, the `.msix` file is available in the GitHub Release assets.

1. Download the `.msix` file from the GitHub Release
2. Log in to https://partner.microsoft.com/dashboard
3. Go to **Windows & Xbox** → **Overview** → **Spinner for Discogs**
4. Click **Start a submission** → **Packages**
5. Upload the `.msix` file — Partner Center will validate and re-sign it for Store distribution
6. Fill in: store listing, screenshots, age rating (3+), pricing (free), categories (Music)
7. Submit for review (~3-5 business days)

---

## Per-Release Checklist

Run these steps for every new app version (substitute `0.3.0` with the actual version):

```bash
# 1. Bump version across pyproject.toml, Cargo.toml, webapp/package.json, snap/snapcraft.yaml
./scripts/bump_version.sh 0.3.0

# 2. AppStream metainfo — add a <release> entry for the new version (~30 sec, manual)
#    Edit packaging/metainfo/com.discogs-spinner.app.metainfo.xml
#    Edit packaging/deb/io.github.edonahue.DiscogsSpinner.metainfo.xml

# 3. Write release notes (required by CI to publish the GitHub Release)
cp docs/releases/TEMPLATE.md docs/releases/v0.3.0.md
# Edit docs/releases/v0.3.0.md — fill in What's New, Bug Fixes, etc.

# 4. Commit everything, tag, and push — CI builds all installers automatically
git add -p
git commit -m "Release 0.3.0"
git tag v0.3.0
git push origin main --tags

# 5. After CI completes
#    a. Generate WinGet manifests (fetches SHA256 automatically)
./scripts/update_winget_manifest.sh 0.3.0
#       - In your microsoft/winget-pkgs fork, copy:
#           packaging/winget/manifests/e/ErichDonahue/SpinnerforDiscogs/0.3.0/
#         to manifests/e/ErichDonahue/SpinnerforDiscogs/0.3.0/
#       - Open PR titled: "Update ErichDonahue.SpinnerforDiscogs to 0.3.0"

#    b. Upload the .msix to Microsoft Partner Center (once account exists)
#       Download from GitHub Release → Partner Center → Spinner for Discogs
#       → Start submission → Packages → upload .msix

#    (Snap Store auto-rebuilds from the pushed tag via snap_publish.yml — no manual step)
```

### Per-store files to update each release

| Store | File | What changes |
|---|---|---|
| All | `pyproject.toml`, `Cargo.toml`, `package.json`, `snap/snapcraft.yaml` | `bump_version.sh` handles this |
| AppStream | `packaging/metainfo/com.discogs-spinner.app.metainfo.xml` | Add `<release>` entry |
| WinGet | `packaging/winget/manifests/e/ErichDonahue/SpinnerforDiscogs/<VERSION>/` | `update_winget_manifest.sh` handles this |
| Microsoft Store | GitHub Release `.msix` → Partner Center upload | Manual (~5 min) |
| Homebrew | `packaging/homebrew/spinner-for-discogs.rb` | `version`, `sha256` for ARM + Intel |
| Flatpak | `packaging/flatpak/com.discogs-spinner.app.yml` | `tag:` and `commit:` fields |
