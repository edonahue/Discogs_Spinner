# RC Release Runbook (`v0.2.0-rc1` and later)

Owner: Engineering  
Date created: 2026-02-26

This runbook defines the exact process for creating and publishing a release
candidate using the `Tagged Release` GitHub Actions workflow.

## Scope

- Release channel: GitHub Releases
- Artifact profiles: `core`, `plus`
- Target OS matrix: Windows, Debian/Linux, macOS
- Workflow source: `.github/workflows/tagged_release.yml`

## Preconditions

1. Working tree is clean.
2. Branch contains all intended RC changes.
3. Global release checks pass:
   - `venv/bin/ruff check .`
   - `venv/bin/python -m mypy src/discogs_player --show-error-codes --hide-error-context`
   - `venv/bin/python -m pytest -q`
   - `./scripts/gui_smoke_test.sh 12`
   - `./scripts/gallery_ux_smoke.sh 12`
   - `bash ./scripts/prepublish_hygiene_check.sh`
4. Draft release notes are prepared from:
   - `docs/RELEASE_NOTES_TEMPLATE.md`

## RC Tag Creation (Primary Path)

Use an annotated RC tag.

```bash
git status -sb
git pull --ff-only
git tag -a v0.2.0-rc1 -m "discogs_player v0.2.0-rc1"
git push origin v0.2.0-rc1
```

Pushing a `v*` tag triggers `Tagged Release`.

## Workflow-Dispatch Fallback

If the tag already exists and you need to republish assets:

1. Open GitHub Actions -> `Tagged Release`
2. Click `Run workflow`
3. Set input `tag` to an existing tag (for example `v0.2.0-rc1`)

## Publish Verification

After workflow completion, verify GitHub Release assets include:

- `discogs_player-core-<os>-<arch>.tar.gz` for each matrix OS
- `discogs_player-plus-<os>-<arch>.tar.gz` for each matrix OS
- `CHECKSUMS.ALL.txt`

Spot-check checksums locally after downloading assets:

```bash
sha256sum CHECKSUMS.ALL.txt
```

On macOS:

```bash
shasum -a 256 CHECKSUMS.ALL.txt
```

## Release Note Publish Checklist

1. Fill `docs/RELEASE_NOTES_TEMPLATE.md` sections.
2. Include links to:
   - `docs/quickstart_windows.md`
   - `docs/quickstart_debian.md`
   - `docs/quickstart_macos.md`
3. Include known limitations and support/reporting path:
   - `dplayer diagnostics --json`
   - issue templates: install/auth/playback

## Post-Publish Actions (Within 24-72h)

1. Execute initial pilot-user install validation.
2. Capture diagnostics for any failures.
3. Open/triage issues and tag blockers before promoting RC to stable.

## Recovery Notes

If a bad RC is published, create a new incremented RC tag (for example
`v0.2.0-rc2`) rather than overwriting existing release history.
