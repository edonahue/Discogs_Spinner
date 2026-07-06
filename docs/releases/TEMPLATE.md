# discogs_player vX.Y.Z

## Summary

- Release type: `stable` | `rc` | `beta`
- Tag: `vX.Y.Z`
- Date: `YYYY-MM-DD`
- Scope: <!-- one-line description of what this release primarily delivers -->

## What's New

<!-- Bullet-point list of new features and significant improvements. -->

- <!-- Feature or improvement 1 -->
- <!-- Feature or improvement 2 -->

## Bug Fixes

<!-- Bullet-point list of bugs fixed since the previous release. -->

- <!-- Bug fix 1 -->

## Packaging and Distribution

- Artifacts included:
  - Windows `.msi`
  - Windows NSIS `.exe`
  - macOS `.dmg`
  - Linux Tauri `.deb`
  - Linux `.AppImage`
  - Linux GTK desktop `.deb`
- Checksum manifest: `CHECKSUMS-INSTALLERS.txt`
- Build workflow: `Installer Build`

## Direct Download Links

- Windows installer (guided): [Spinner for Discogs_X.Y.Z_x64-setup.exe](https://github.com/edonahue/spinner-for-discogs/releases/download/vX.Y.Z/Spinner-for-Discogs_X.Y.Z_x64-setup.exe)
- Windows installer (MSI): [Spinner for Discogs_X.Y.Z_x64_en-US.msi](https://github.com/edonahue/spinner-for-discogs/releases/download/vX.Y.Z/Spinner-for-Discogs_X.Y.Z_x64_en-US.msi)
- Linux desktop installer (GTK): [discogs-spinner-gtk4_X.Y.Z_amd64.deb](https://github.com/edonahue/spinner-for-discogs/releases/download/vX.Y.Z/discogs-spinner-gtk4_X.Y.Z_amd64.deb)
- Linux desktop installer (Tauri): [discogs-spinner-tauri_X.Y.Z_amd64.deb](https://github.com/edonahue/spinner-for-discogs/releases/download/vX.Y.Z/discogs-spinner-tauri_X.Y.Z_amd64.deb)
- Linux portable installer: [Spinner for Discogs_X.Y.Z_amd64.AppImage](https://github.com/edonahue/spinner-for-discogs/releases/download/vX.Y.Z/Spinner-for-Discogs_X.Y.Z_amd64.AppImage)
- macOS installer (Apple Silicon): [Spinner for Discogs_X.Y.Z_aarch64.dmg](https://github.com/edonahue/spinner-for-discogs/releases/download/vX.Y.Z/Spinner-for-Discogs_X.Y.Z_aarch64.dmg)
- macOS installer (Intel): [Spinner for Discogs_X.Y.Z_x64.dmg](https://github.com/edonahue/spinner-for-discogs/releases/download/vX.Y.Z/Spinner-for-Discogs_X.Y.Z_x64.dmg)
- Checksums: [CHECKSUMS-INSTALLERS.txt](https://github.com/edonahue/spinner-for-discogs/releases/download/vX.Y.Z/CHECKSUMS-INSTALLERS.txt)

## Install and Setup

- Windows quickstart: [docs/quickstart_windows.md](../quickstart_windows.md)
- Debian quickstart: [docs/quickstart_debian.md](../quickstart_debian.md)
- macOS quickstart: [docs/quickstart_macos.md](../quickstart_macos.md)

## Validation Evidence

- `ruff`: pass
- `mypy`: pass
- `pytest -q`: pass (`NNN passed, N skipped`)
- Web build: pass (`npm run build`)
- Playwright smoke: pass (`npm run test:e2e`)
- Installer workflow: pass (`Installer Build` run <!-- run ID -->)
- Windows MSI smoke: pass (`Windows MSI Smoke` run <!-- run ID -->)

## Known Limitations

<!-- List any known issues, workarounds, or missing functionality. -->

- <!-- Known limitation 1 -->

## Upgrade / Migration Notes

- Breaking changes: <!-- none, or describe them -->
- Existing local data and config paths are unchanged.
- <!-- Any other migration steps required -->

## Reporting Issues

When filing issues, attach:

- `dplayer diagnostics --json`
- reproduction steps
- OS and installer path details

Issue template areas:

- [install failure](https://github.com/edonahue/spinner-for-discogs/issues/new?template=install_failure.yml)
- [auth/setup failure](https://github.com/edonahue/spinner-for-discogs/issues/new?template=auth_failure.yml)
- [playback failure](https://github.com/edonahue/spinner-for-discogs/issues/new?template=playback_failure.yml)

## Acknowledgements

- <!-- Contributors, testers, or notable mentions -->
