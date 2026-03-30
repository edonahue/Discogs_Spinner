# Public Release Runbook (`v0.2.0` and later)

Owner: Engineering  
Date created: 2026-03-30

This runbook defines the exact process for creating and publishing a public installer release using the `Installer Build` GitHub Actions workflow.

## Scope

- Release channel: GitHub Releases
- Primary workflow: `.github/workflows/installer_build.yml`
- Target OS matrix: Windows, Debian/Linux, macOS
- Release posture: installer-first, public-facing

## Preconditions

1. Working tree is clean.
2. The branch contains the intended release docs and installer workflow changes.
3. `pyproject.toml` version matches the intended stable tag.
4. Global validation passes:
   - `venv/bin/python -m ruff check .`
   - `venv/bin/python -m mypy src/discogs_player --show-error-codes --hide-error-context`
   - `venv/bin/python -m pytest -q`
   - `npm run build` in `webapp/`
   - `npm run test:e2e` in `webapp/`
5. Latest installer evidence is green:
   - `Installer Build` passes on Windows, Ubuntu, `macos-14`, and `macos-15-intel`
   - Debian Docker clean-install validation passes
6. Release notes exist at `docs/releases/<tag>.md`.
7. `docs/RELEASE_NOTES_TEMPLATE.md` has been copied and tailored for the release.

## Tag Creation

Use an annotated stable tag.

```bash
git status -sb
git pull --ff-only
git tag -a v0.2.0 -m "discogs_player v0.2.0"
git push origin v0.2.0
```

Pushing a `v*` tag triggers `Installer Build`, which publishes installer assets directly to the GitHub Release for that tag.

## Publish Verification

After workflow completion, verify GitHub Release assets include:

- Windows `.msi`
- Windows NSIS `.exe`
- macOS `.dmg`
- Linux Tauri `.deb`
- Linux `.AppImage`
- GTK desktop `.deb`
- `CHECKSUMS-INSTALLERS.txt`

Spot-check the checksum manifest after downloading assets:

```bash
sha256sum CHECKSUMS-INSTALLERS.txt
```

On macOS:

```bash
shasum -a 256 CHECKSUMS-INSTALLERS.txt
```

## Release Note Requirements

The release body is loaded from `docs/releases/<tag>.md`. Before tagging, confirm that file includes:

- installer asset summary
- links to the Windows, Debian, and macOS quickstarts
- validation evidence from the current installer workflow
- known limitations and support/reporting guidance
- structure aligned with `docs/RELEASE_NOTES_TEMPLATE.md`

## Legacy Tarballs

The old tarball build remains available only as the manual workflow `.github/workflows/tagged_release.yml` (`Legacy Tarball Release`). It is no longer the primary public release path.

## Post-Publish Actions (Within 24-72h)

1. Watch install/auth/playback issues from first public users.
2. Record installer friction in the backlog and release checklist follow-up.
3. Schedule the slow Windows MSI smoke workflow once it is available on the default branch.
