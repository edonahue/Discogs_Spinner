# Scripts

Utility scripts for building, releasing, testing, and operating Discogs Spinner.

## Build & packaging

| Script | Purpose |
|--------|---------|
| `build_sidecar.sh` | PyInstaller bundle of `dplayer-api` for Tauri sidecar (per-platform) |
| `validate_tauri_sidecar_contract.py` | Verifies Tauri config, target triple naming, and sidecar binary presence stay in sync |
| `validate_tauri_linux_real_build.sh` | Runs the real Linux Tauri sidecar + webapp + bundle build flow end to end |
| `validate_tauri_linux_bundle.sh` | Verifies Linux Tauri `.deb` and `.AppImage` bundles include the expected sidecar |
| `validate_tauri_macos_bundle.sh` | Verifies macOS Tauri `.dmg` bundles include the expected sidecar inside the app bundle |
| `validate_tauri_windows_bundle.ps1` | Verifies Windows Tauri `.msi` and NSIS `.exe` bundles include the expected sidecar |
| `build_deb.sh` | fpm-based Debian `.deb` package for GTK4 desktop app (build with Python 3.10) |
| `build_artifacts.sh` | Aggregates all release artifacts after platform builds |
| `validate_linux_packaging_metadata.py` | Validates GTK `.deb` desktop entry and AppStream metadata before release |

## Release

| Script | Purpose |
|--------|---------|
| `bump_version.sh` | Atomically bumps the version across `pyproject.toml`, `Cargo.toml`, `package.json`, and `snapcraft.yaml` |
| `update_winget_manifest.sh` | Generates the WinGet manifest for a new release, fetching SHA256s from the GitHub Release |
| `gen_flatpak_deps.sh` | Generates `python3-deps.json` for the Flathub build via `flatpak-pip-generator` |

## Screenshots & media

| Script | Purpose |
|--------|---------|
| `headless_screenshot.py` | Headless Xvfb screenshot capture + GIF assembly (preferred) |
| `capture_readme_media.sh` | Semi-automated screenshot capture (requires X11/Wayland desktop) |
| `generate_readme_media.py` | Synthetic media generation (PIL-based, no display required) |

## Installation

| Script | Purpose |
|--------|---------|
| `install_desktop_app.sh` | Installs desktop launcher and registers MIME types |
| `uninstall_desktop_app.sh` | Removes desktop launcher and MIME registrations |

## CI & validation

| Script | Purpose |
|--------|---------|
| `ci_pilot_validation.py` | Validates pilot release artifacts in CI |
| `prepublish_hygiene_check.sh` | Pre-release linting, test, and hygiene checks |
| `gui_smoke_test.sh` | Quick CLI-driven GUI smoke test |
| `gallery_ux_smoke.sh` | Gallery UX smoke test |

## Sync & scheduling

| Script | Purpose |
|--------|---------|
| `run_scheduled_sync.sh` | Runs a Discogs collection sync (called from cron) |
| `setup_sync_schedule.sh` | Installs cron job for daily sync |

## Spotify

| Script | Purpose |
|--------|---------|
| `spotify_live_smoke.sh` | Live Spotify integration smoke test |
| `spotify_catalog_map_slow.sh` | Slow full-catalog Spotify match (batch, throttled) |
| `spotify_mapping_report.sh` | Prints Spotify mapping coverage report |

## Utilities

| Script | Purpose |
|--------|---------|
| `convert_discofy_bootstrap.py` | Migrates data from Discofy bootstrap export |

## Related docs

- [Public release runbook](../docs/PUBLIC_RELEASE_RUNBOOK.md)
- [Current stable release notes](../docs/releases/v0.2.3.md)
- [Previous release notes](../docs/releases/v0.2.2.md)
- [Windows quickstart](../docs/quickstart_windows.md)
- [macOS quickstart](../docs/quickstart_macos.md)
- [Debian quickstart](../docs/quickstart_debian.md)
- [Code signing guide](../docs/SIGNING.md)
- [README media guide](../docs/media/README.md)
