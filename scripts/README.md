# Scripts

Utility scripts for building, releasing, testing, and operating Discogs Spinner.

## Build & packaging

| Script | Purpose |
|--------|---------|
| `build_sidecar.sh` | PyInstaller bundle of `dplayer-api` for Tauri sidecar (per-platform) |
| `build_deb.sh` | fpm-based Debian `.deb` package for GTK4 desktop app |
| `build_artifacts.sh` | Aggregates all release artifacts after platform builds |

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
