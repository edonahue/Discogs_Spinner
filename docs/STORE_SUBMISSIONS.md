# Store Submissions Guide

This document covers the end-to-end submission steps for each official distribution
channel. Complete steps in the order shown — later channels depend on earlier ones.

---

## Submission Readiness Snapshot

At-a-glance status of every channel and the single next blocker for the ones that
are not yet live. Full per-channel steps follow below.

| Channel | Status | Next blocker / action |
|---|---|---|
| WinGet | ✅ Live | Per-release: `./scripts/update_winget_manifest.sh <version>` then PR |
| Snap Store | ✅ Live | Auto-publishes on `v*` tag via `snap_publish.yml` |
| Homebrew Cask | 🟡 Ready, blocked on macOS notarization | Notarize the `.dmg` (needs Apple Developer Program), then submit the PR — formula SHA256s for 0.2.2 are already filled in |
| Flathub | 🟡 Ready, needs deps JSON | Run `./scripts/gen_flatpak_deps.sh`, set the real commit SHA in the manifest, then submit the PR — screenshots in the metainfo are already populated |
| Microsoft Store | 🟡 Ready, blocked on Partner Center | Register Partner Center ($19), replace the `TODO(partner-center)` Identity/Publisher in `packaging/msix/Package.appxmanifest`, convert the NSIS `.exe` to MSIX, upload |

Items marked 🟡 require an external account, paid program, or a clean OS — the in-repo
prep for each is done; the remaining work is the manual submission step.

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
Required for: Microsoft Store submission.
- Register at https://partner.microsoft.com/dashboard ($19 one-time)
- Reserve the app name **"Spinner for Discogs"**
- No code changes needed — CI already produces the NSIS `.exe` that Partner Center accepts directly

---

## Channel 1: Homebrew Cask (macOS)

**Prerequisites:** Apple Developer Program, notarized `.dmg` on latest release.

**File:** `packaging/homebrew/spinner-for-discogs.rb`

1. Download the notarized `.dmg` files for both architectures from the GitHub Release
2. Confirm the `sha256` values in the formula match the released `.dmg` files (already
   filled in for 0.2.2; recompute with `shasum -a 256 <file>.dmg` for new releases)
3. Fork https://github.com/Homebrew/homebrew-cask
4. Copy the formula to `Casks/s/spinner-for-discogs.rb`
5. Run locally: `brew install --cask ./Casks/s/spinner-for-discogs.rb`
6. Run: `brew audit --cask --new spinner-for-discogs`
7. Submit PR to homebrew/homebrew-cask

---

## Channel 2: WinGet (Windows Package Manager)

**Prerequisites:** None (no signing required for WinGet).

**Current status: Live.** PR [microsoft/winget-pkgs#384707](https://github.com/microsoft/winget-pkgs/pull/384707) was merged on 2026-06-13. `winget install ErichDonahue.SpinnerforDiscogs` works for end users now. The wingetbot publish pipeline confirmed success.

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
   ./scripts/gen_flatpak_deps.sh
   ```
   This wraps `flatpak-pip-generator` with the exact runtime dependency set and writes
   `packaging/flatpak/python3-deps.json`. Then uncomment the `- python3-deps.json` line
   in the Flatpak manifest.

3. Screenshots: the `<screenshots>` block in
   `packaging/metainfo/com.discogs-spinner.app.metainfo.xml` is already populated with the
   five `docs/media/screenshots/*.png` images. Confirm they meet Flathub's size guidance
   (1248×702 or 624×351) and refresh them if the UI has changed.

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

### Current status

- Public listing verified in an unauthenticated browser on 2026-06-09.
- Store install smoke verified on Pop!_OS/COSMIC with:
  `sudo snap install spinner-for-discogs` and `spinner-for-discogs`.
- The app launched successfully, but first-run polish still needs work. Known
  launch noise includes GTK/GIO/libproxy warnings, repeated GLib schema symlink
  messages, a COSMIC dconf profile fallback, and missing IM/media module
  warnings. Treat these as polish debt unless a user-visible launch failure
  appears.
- **Schema warnings mitigation (needs verification):** `snap/snapcraft.yaml` now
  precompiles the staged GSettings schemas at prime time
  (`glib-compile-schemas` in `override-prime`), which should remove the repeated
  GLib schema symlink/compile messages. This has not yet been verified against a
  real snap rebuild — confirm on the next build with
  `snap run spinner-for-discogs` and check that the schema warnings are gone. The
  remaining libproxy / COSMIC dconf / IM-module messages originate in the host
  desktop environment and are not fixable from the package.

### Listing metadata

Keep the Snap dashboard listing aligned with `snap/snapcraft.yaml`.

- Title: `Spinner for Discogs`
- Primary category: `Music and Audio`
- Secondary category: `Utilities`
- Summary: `Pick, browse, and value your Discogs vinyl collection`
- License: `MIT`
- Primary website: https://github.com/edonahue/Discogs_Spinner
- Source code: https://github.com/edonahue/Discogs_Spinner
- Issues: https://github.com/edonahue/Discogs_Spinner/issues
- Contacts: https://github.com/edonahue/Discogs_Spinner/issues
- Snap icon: `desktop_shell/icons/icon.png`
- Screenshots, in order:
  - `docs/media/screenshots/01-browse-gallery.png`
  - `docs/media/screenshots/02-spin-result.png`
  - `docs/media/screenshots/03-market-value-dashboard.png`
  - `docs/media/screenshots/04-wantlist-view.png`
  - `docs/media/screenshots/05-setup-wizard.png`

Description:

```markdown
Spinner for Discogs is a local-first desktop companion for vinyl collectors who keep their shelves in Discogs.

Connect your Discogs account with a personal access token, sync your collection, then browse your records, spin a random album, inspect release details, track market value, and keep wantlist context close without living in browser tabs.

What you can do:

- Browse and search your Discogs collection and wantlist
- Spin a random record when you cannot decide what to play
- View cover art, release details, tracklists, and market prices
- Check collection value and wantlist context from one desktop app
- Optionally hand playback to Spotify or YouTube Music

First run is designed to be quick: install the app, paste your Discogs personal access token into the setup wizard, sync once, and start browsing your records.

Notes:

- A free Discogs account and personal access token are required.
- Spotify and YouTube Music are optional integrations.
- Spinner for Discogs does not stream audio itself; it controls or opens external playback services when configured.
- This is an unofficial third-party app and is not affiliated with Discogs.
```

### Automated publishing

**Recommended: GitHub Actions tag publishing.**

Workflow: `.github/workflows/snap_publish.yml`

The workflow runs on `v*` tag pushes and manual dispatches. It builds the snap
with `snapcore/action-build@v1` and publishes it to `stable` with
`snapcore/action-publish@v1`.

Required GitHub repository secret:

- `SNAPCRAFT_STORE_CREDENTIALS`

Check or add it in GitHub:

1. Open `edonahue/Discogs_Spinner` on GitHub.
2. Go to **Settings** → **Secrets and variables** → **Actions**.
3. Open **Repository secrets**.
4. Confirm `SNAPCRAFT_STORE_CREDENTIALS` exists, or add it with
   **New repository secret**.

Generate credentials locally with Snapcraft, then paste the file contents into
that repository secret:

```bash
snapcraft login
snapcraft export-login --snaps spinner-for-discogs --channels stable snapcraft-credentials.txt
```

Keep `snapcraft-credentials.txt` out of git. It is ignored locally and should be
deleted or moved outside the repository after the GitHub secret is set.

**Alternative: Snapcraft connected build service**

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

### Future Snap polish goals

- Tune the first-time user experience so a fresh snap launch immediately explains
  the Discogs token requirement and next step.
- Reduce harmless terminal warning noise from GTK/GIO/libproxy/schema setup where
  practical. (GSettings schema precompile is now wired in `snapcraft.yaml`; verify
  it on the next snap build and tackle any residual GTK/GIO noise from there.)
- Add a featured banner sized for Snapcraft once the visual direction is stable.
- Add a short hosted demo video after the first-run flow is polished.

---

## Channel 5: Microsoft Store

**Prerequisites:** Microsoft Partner Center account ($19 one-time), Windows machine with
[MSIX Packaging Tool](https://apps.microsoft.com/detail/9n5lw3jbcxkf) (free, from Microsoft Store).

Tauri v2 does not produce MSIX directly. The NSIS `.exe` from CI must be converted to MSIX
using the MSIX Packaging Tool before submission. No Windows code signing certificate is needed —
Partner Center signs the package for Store distribution.

1. Download the `Discogs.Spinner_<VERSION>_x64-setup.exe` from the GitHub Release
2. Open **MSIX Packaging Tool** → "Application package" → point it at the `.exe`
3. Follow the wizard: install the app in a VM/clean environment, capture the installation, export `.msix`
4. Log in to https://partner.microsoft.com/dashboard
5. Go to **Windows & Xbox** → **Overview** → **Spinner for Discogs**
6. Click **Start a submission** → **Packages** → upload the `.msix`
7. Fill in: store listing, screenshots (reuse Snap Store screenshots), age rating (3+), pricing (free), category Music
8. Submit for review (~3-5 business days)

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

#    b. Microsoft Store (once Partner Center account exists):
#       Download Discogs.Spinner_X.Y.Z_x64-setup.exe from GitHub Release
#       → Convert to .msix with MSIX Packaging Tool (free, from Microsoft Store)
#       → Partner Center → Spinner for Discogs → Start submission → Packages → upload .msix

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
