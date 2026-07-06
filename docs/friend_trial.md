# Friend Trial Guide

Use this when you want a friend to try the public installers without asking them to learn the whole project first.
For a shorter pass/fail runbook, use [`docs/friend_trial_checklist.md`](friend_trial_checklist.md).

## What To Download

- Windows: use the guided installer first: [Windows setup EXE (v0.2.3 legacy filename)](https://github.com/edonahue/spinner-for-discogs/releases/download/v0.2.3/Discogs.Spinner_0.2.3_x64-setup.exe)
- Windows fallback for managed installs: [Windows MSI (v0.2.3 legacy filename)](https://github.com/edonahue/spinner-for-discogs/releases/download/v0.2.3/Discogs.Spinner_0.2.3_x64_en-US.msi)
- macOS Apple Silicon: [macOS Apple Silicon DMG (v0.2.3 legacy filename)](https://github.com/edonahue/spinner-for-discogs/releases/download/v0.2.3/Discogs.Spinner_0.2.3_aarch64.dmg)
- macOS Intel: [macOS Intel DMG (v0.2.3 legacy filename)](https://github.com/edonahue/spinner-for-discogs/releases/download/v0.2.3/Discogs.Spinner_0.2.3_x64.dmg)
- Linux Snap Store: [Spinner for Discogs on Snapcraft](https://snapcraft.io/spinner-for-discogs), or `sudo snap install spinner-for-discogs` if `snapd` is already set up
- Debian/Ubuntu direct package: [discogs-spinner-gtk4_0.2.3_amd64.deb](https://github.com/edonahue/spinner-for-discogs/releases/download/v0.2.3/discogs-spinner-gtk4_0.2.3_amd64.deb)
- Linux portable fallback: [Linux AppImage (v0.2.3 legacy filename)](https://github.com/edonahue/spinner-for-discogs/releases/download/v0.2.3/Discogs.Spinner_0.2.3_amd64.AppImage)
- Linux alternate desktop build: [discogs-spinner-tauri_0.2.3_amd64.deb](https://github.com/edonahue/spinner-for-discogs/releases/download/v0.2.3/discogs-spinner-tauri_0.2.3_amd64.deb)
- Checksums: [CHECKSUMS-INSTALLERS.txt](https://github.com/edonahue/spinner-for-discogs/releases/download/v0.2.3/CHECKSUMS-INSTALLERS.txt)

If you would rather browse the full release page first, start here: [Download the latest stable release](https://github.com/edonahue/spinner-for-discogs/releases/latest)

## What To Try

1. Download the recommended installer for your OS and install the app.
2. Launch **Spinner for Discogs**.
3. Confirm you either:
   - reach the setup wizard, or
   - see your collection after setup and first sync.
4. If you use Spotify features, stop after verifying auth/setup prompts make sense. Full playback testing is optional for friend trials.
5. Optional quick quality pass: run `dplayer insights` and confirm the output is understandable.

## What Feedback Is Most Helpful

Please report any of these:

- I was not sure which file to download
- Windows SmartScreen or macOS Gatekeeper instructions were confusing
- Linux package choices were confusing
- The app did not launch after install
- The setup wizard was confusing or failed
- I did not understand optional provider status (ready/degraded/unavailable)
- The app launched, but collection sync or basic browsing failed

## How To Report A Problem

Include:

- your OS and version
- which installer you used
- the exact message or warning you saw
- a screenshot if possible
- whether the app reached the setup screen

Direct GitHub issue links:

- [Install failure](https://github.com/edonahue/spinner-for-discogs/issues/new?template=install_failure.yml)
- [Auth/setup failure](https://github.com/edonahue/spinner-for-discogs/issues/new?template=auth_failure.yml)
- [Playback failure](https://github.com/edonahue/spinner-for-discogs/issues/new?template=playback_failure.yml)

If you are sending the link personally, a plain-text message with the same details is also enough.
