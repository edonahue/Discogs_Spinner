# Release Checklist First Pass (2026-02-26)

Date: 2026-02-26 (UTC)  
Scope: First execution pass of `docs/RELEASE_CHECKLIST_WINDOWS_DEBIAN_MACOS.md` and `docs/RC_RELEASE_RUNBOOK.md`.

Follow-up status for the currently published RC is tracked in:

- `docs/RELEASE_CHECKLIST_STATUS_v0.2.0-rc4_2026-02-26.md`

## Run Scope And Context

- Branch at run start: `master`
- Working tree at run start: clean (`git status -sb`)
- RC tag present: `v0.2.0-rc1`
- Release notes draft present: `docs/releases/v0.2.0-rc1.md`

## Commands Executed

```bash
bash ./scripts/prepublish_hygiene_check.sh
venv/bin/ruff check .
venv/bin/python -m mypy src/discogs_player --show-error-codes --hide-error-context
venv/bin/python -m pytest -q
npm --prefix webapp run build
./scripts/gui_smoke_test.sh 12
./scripts/gallery_ux_smoke.sh 12
```

## Results

- `prepublish_hygiene_check.sh`: PASS
- `ruff check .`: PASS (`All checks passed!`)
- `mypy`: PASS (`Success: no issues found in 92 source files`)
- `pytest -q`: PASS (`369 passed, 3 skipped in 43.43s`)
- `npm --prefix webapp run build`: PASS (Vite build completed)
- `gui_smoke_test.sh 12`: PASS (`ok: true`)
- `gallery_ux_smoke.sh 12`: PASS (`ok: true`)
- `git push ... v0.2.0-rc1`: PASS (existing local RC tag pushed to GitHub)
- `git ls-remote --tags origin v0.2.0-rc1*`: PASS (remote tag confirmed)

## Global Pre-Release Gate Status

- [x] Working tree was clean at run start and RC tag exists.
- [x] `docs/RC_RELEASE_RUNBOOK.md` reviewed.
- [x] Release notes are drafted (`docs/releases/v0.2.0-rc1.md`).
- [x] `venv/bin/ruff check .` passes.
- [x] `venv/bin/python -m mypy src/discogs_player --show-error-codes --hide-error-context` passes.
- [x] `venv/bin/python -m pytest -q` passes.
- [x] `./scripts/gui_smoke_test.sh 12` passes.
- [x] `./scripts/gallery_ux_smoke.sh 12` passes.
- [x] No secrets/personal-data violations found by `prepublish_hygiene_check.sh`.
- [ ] Legal/compliance docs reviewed with explicit sign-off (`LICENSE`, `PRIVACY.md`, `TERMS.md`, `TRADEMARKS.md`, `COMPLIANCE.md`).

## Remaining Checklist Scope

- Stage 1 (Windows), Stage 2 (Debian), and Stage 3 (macOS) validation items are still pending.
- Publish-gate and 72-hour post-release follow-up items are still pending.

## Tagged Release Workflow Status (v0.2.0-rc2)

- Triggered by pushing tag `v0.2.0-rc2`.
- Workflow run: `https://github.com/edonahue/Discogs_Spinner/actions/runs/22425924450`
- Run status: `completed` with `failure`.
- Job status:
  - `Build Release Artifacts (ubuntu-latest)`: success
  - `Build Release Artifacts (windows-latest)`: success
  - `Build Release Artifacts (macos-latest)`: failure
  - `Publish GitHub Release`: skipped
- Failed step on macOS job: `Build core and plus artifacts`.
- `GET /releases/tags/v0.2.0-rc2` returned `404` immediately after run completion, confirming release publication did not complete for this tag.
