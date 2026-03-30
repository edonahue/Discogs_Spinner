# Release Notes Template

Use this template for installer-first GitHub releases.

Suggested title format:

- `discogs_player vX.Y.Z`

---

## Summary

- Release type: `<stable|prerelease>`
- Tag: `<vX.Y.Z>`
- Date: `<YYYY-MM-DD>`
- Scope: `<short release summary>`

## Highlights

- `<feature/high-impact change 1>`
- `<feature/high-impact change 2>`
- `<feature/high-impact change 3>`

## Packaging And Distribution

- Artifacts included:
  - Windows: `.msi` and NSIS `.exe`
  - macOS: `.dmg`
  - Linux: Tauri `.deb` and `.AppImage`
  - Linux desktop: GTK `.deb`
- Checksum manifest: `CHECKSUMS-INSTALLERS.txt`
- Build workflow: `Installer Build`

## Install And Setup

- Windows quickstart: `docs/quickstart_windows.md`
- Debian quickstart: `docs/quickstart_debian.md`
- macOS quickstart: `docs/quickstart_macos.md`

## Validation Evidence

- `ruff`: `<pass/fail + details>`
- `mypy`: `<pass/fail + details>`
- `pytest -q`: `<pass/fail + counts>`
- GUI smoke: `<pass/fail>`
- Gallery UX smoke: `<pass/fail>`
- Installer workflow: `<run id + pass/fail>`

## Known Limitations

- `<limitation 1>`
- `<limitation 2>`
- `<limitation 3>`

## Upgrade / Migration Notes

- `<breaking change or "none">`
- `<env/config changes>`
- `<data-path or DB behavior notes>`

## Reporting Issues

When filing issues, attach:

- `dplayer diagnostics --json`
- reproduction steps
- relevant OS and install path

Issue templates:

- install failure
- auth/setup failure
- playback failure

## Acknowledgements

- `<contributors/testers>`

---

For release execution steps, use:

- `docs/PUBLIC_RELEASE_RUNBOOK.md`
