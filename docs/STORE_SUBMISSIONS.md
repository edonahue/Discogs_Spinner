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
- Note your assigned **Publisher Display Name** and **Publisher ID** (e.g. `CN=XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX`)
- Update `desktop_shell/src-tauri/tauri.conf.json` → `bundle.windows.msix.publisherDisplayName`
  to match your registered Publisher Display Name exactly

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

**Files:** `packaging/winget/manifests/e/EricDonahue/SpinnerforDiscogs/0.2.0/`

1. Download the `.exe` (NSIS installer) and `.msi` (WiX installer) from the GitHub Release
2. Compute SHA256 checksums and replace `PLACEHOLDER_SHA256_REPLACE_BEFORE_PR_SUBMISSION`
   in `EricDonahue.SpinnerforDiscogs.installer.yaml`
3. Validate manifests locally (requires `winget-cli`):
   ```
   winget validate --manifest packaging/winget/manifests/e/EricDonahue/SpinnerforDiscogs/0.2.0/
   ```
4. Fork https://github.com/microsoft/winget-pkgs
5. Copy the entire `packaging/winget/manifests/e/EricDonahue/SpinnerforDiscogs/` directory
   to the same path in your fork
6. Submit PR — WinGet bot will auto-validate manifests

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

**Prerequisites:** None.

**File:** `packaging/snap/snapcraft.yaml`

1. Install snapcraft: `sudo snap install snapcraft --classic`
2. Create a snapcraft.io account at https://snapcraft.io/account
3. Build the snap from the project root:
   ```bash
   cd packaging/snap
   snapcraft
   ```
4. Review the built snap:
   ```bash
   snap install spinner-for-discogs_0.2.0_amd64.snap --dangerous
   snap run spinner-for-discogs
   ```
5. Login and upload:
   ```bash
   snapcraft login
   snapcraft upload spinner-for-discogs_0.2.0_amd64.snap --release=stable
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

## Updating for New Releases

When a new version is released, update the following files before tagging:

| File | What to update |
|---|---|
| `packaging/winget/manifests/e/EricDonahue/SpinnerforDiscogs/<NEW_VERSION>/` | Copy and update installer YAML with new URLs + SHA256 hashes |
| `packaging/homebrew/spinner-for-discogs.rb` | Update `version`, `sha256` for both architectures |
| `packaging/flatpak/com.discogs-spinner.app.yml` | Update `tag:` and `commit:` |
| `packaging/metainfo/com.discogs-spinner.app.metainfo.xml` | Add new `<release>` entry |
| `packaging/snap/snapcraft.yaml` | Update `version:` |

The `scripts/bump_version.sh` script handles `pyproject.toml`, `Cargo.toml`, and
`package.json` version bumps. Store manifest files must be updated manually.
