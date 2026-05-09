# Friend Trial Guide

Use this when you want a friend to try the public installers without asking them to learn the whole project first.
For a shorter pass/fail runbook, use [`docs/friend_trial_checklist.md`](friend_trial_checklist.md).

## What To Download

- Windows: use the guided installer first: [Discogs Spinner_0.2.0_x64-setup.exe](https://github.com/edonahue/Discogs_Spinner/releases/download/v0.2.0/Discogs.Spinner_0.2.0_x64-setup.exe)
- Windows fallback for managed installs: [Discogs Spinner_0.2.0_x64_en-US.msi](https://github.com/edonahue/Discogs_Spinner/releases/download/v0.2.0/Discogs.Spinner_0.2.0_x64_en-US.msi)
- macOS Apple Silicon: [Discogs Spinner_0.2.0_aarch64.dmg](https://github.com/edonahue/Discogs_Spinner/releases/download/v0.2.0/Discogs.Spinner_0.2.0_aarch64.dmg)
- macOS Intel: [Discogs Spinner_0.2.0_x64.dmg](https://github.com/edonahue/Discogs_Spinner/releases/download/v0.2.0/Discogs.Spinner_0.2.0_x64.dmg)
- Debian/Ubuntu desktop: [discogs-spinner-gtk4_0.2.0_amd64.deb](https://github.com/edonahue/Discogs_Spinner/releases/download/v0.2.0/discogs-spinner-gtk4_0.2.0_amd64.deb)
- Linux portable fallback: [Discogs Spinner_0.2.0_amd64.AppImage](https://github.com/edonahue/Discogs_Spinner/releases/download/v0.2.0/Discogs.Spinner_0.2.0_amd64.AppImage)
- Linux alternate desktop build: [discogs-spinner-tauri_0.2.0_amd64.deb](https://github.com/edonahue/Discogs_Spinner/releases/download/v0.2.0/discogs-spinner-tauri_0.2.0_amd64.deb)
- Checksums: [CHECKSUMS-INSTALLERS.txt](https://github.com/edonahue/Discogs_Spinner/releases/download/v0.2.0/CHECKSUMS-INSTALLERS.txt)

If you would rather browse the full release page first, start here: [Download the latest stable release](https://github.com/edonahue/Discogs_Spinner/releases/latest)

## What To Try

1. Download the recommended installer for your OS and install the app.
2. Launch **Discogs Spinner**.
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

- [Install failure](https://github.com/edonahue/Discogs_Spinner/issues/new?template=install_failure.yml)
- [Auth/setup failure](https://github.com/edonahue/Discogs_Spinner/issues/new?template=auth_failure.yml)
- [Playback failure](https://github.com/edonahue/Discogs_Spinner/issues/new?template=playback_failure.yml)

If you are sending the link personally, a plain-text message with the same details is also enough.
