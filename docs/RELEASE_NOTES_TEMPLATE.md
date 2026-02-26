# Release Notes Template

Use this template for RC and stable GitHub releases.

Suggested title format:

- `discogs_player vX.Y.Z-rcN`
- `discogs_player vX.Y.Z`

---

## Summary

- Release type: `<rc|stable>`
- Tag: `<vX.Y.Z-rcN>`
- Date: `<YYYY-MM-DD>`
- Scope: `<short release summary>`

## Highlights

- `<feature/high-impact change 1>`
- `<feature/high-impact change 2>`
- `<feature/high-impact change 3>`

## Packaging And Distribution

- Artifacts included:
  - `discogs_player-core-<os>-<arch>.tar.gz`
  - `discogs_player-plus-<os>-<arch>.tar.gz`
- Checksum manifest: `CHECKSUMS.ALL.txt`
- Build workflow: `Tagged Release`

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

- `docs/RC_RELEASE_RUNBOOK.md`
