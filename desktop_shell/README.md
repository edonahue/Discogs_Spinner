# Discogs Spinner Desktop Shell

Tauri-oriented desktop packaging scaffold for cross-platform distribution.

This shell is for library browsing and external playback control, not embedded
audio streaming.

## Direction

- Runtime target: Tauri wrapping `../webapp/dist`.
- Local backend target: `dplayer-api`.
- Distribution targets: Windows, macOS, Debian Linux.

## Current state

- `tauri.conf.json` is present as a baseline config scaffold.
- Full Tauri project bootstrap (`src-tauri/`, signing, installers, notarization) is not
  implemented yet.
- Packaging/signing is intentionally deferred to later release stages.

## Repository role

This folder documents and anchors desktop packaging intent while the project
prioritizes core CLI/API/web stability and release-candidate workflows.

For staged execution order, see:

- `../docs/CROSS_PLATFORM_IMPLEMENTATION_ROADMAP.md`
- `../docs/RELEASE_CHECKLIST_WINDOWS_DEBIAN_MACOS.md`
