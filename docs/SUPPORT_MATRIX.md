# Support Matrix

This matrix defines the recommended support posture for the current public release line and the `1.0` target.

## First-Class Surfaces

- CLI (`dplayer`)
- Native installers

## Secondary Surfaces

- Web app / local API parity
- WSL2 GTK path
- Source installs for non-developer end users

## OS And Installer Matrix

| OS / environment | Status | Recommended path | Secondary path | Notes |
|---|---|---|---|---|
| Windows 10/11 x64 | First-class | NSIS `-setup.exe` | `.msi` | `1.0` should remove SmartScreen friction via signing |
| macOS 13+ | First-class | `.dmg` | source install for CLI | `1.0` should remove Gatekeeper workaround via signing + notarization |
| Debian 12+ / Ubuntu equivalent | First-class | GTK `.deb` | `.AppImage`, Linux Tauri `.deb` | GTK `.deb` is the default desktop recommendation |
| CLI on supported OSes | First-class | `dplayer` | source install | Core workflows must remain SSH-usable |
| Web app / local API | Secondary | browser-based quickstart | native installers | Valuable, but not a `1.0` parity blocker |
| Windows WSL2 GTK | Secondary | WSL2 quickstart | native Windows installer | Advanced path, not the default user journey |

## Core Supported Workflows

The following are part of the expected support contract:

- Discogs token setup
- `setup`, `sync`, `status`, `list`, `spin`
- collection browse/detail flows
- wantlist browse/detail flows
- market value views and refresh basics
- graceful failure when optional provider integrations are unavailable

## Optional / Best-Effort Workflows

- Spotify provider setup and playback control
- YouTube Music/open-in-browser helpers
- advanced import/export and power-user data flows
- source-install and development-environment setup

## 1.0 Support Expectations

For `v1.0.0`, support docs and release notes should assume:

- Windows and macOS installers are signed
- the recommended installer path per OS is the shortest documented path
- issue templates and `dplayer diagnostics --json` are part of normal support triage
