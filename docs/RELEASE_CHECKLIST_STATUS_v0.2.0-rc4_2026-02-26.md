# Release Checklist Status (v0.2.0-rc4)

Date: 2026-02-26 (UTC)  
Source checklist: `docs/RELEASE_CHECKLIST_WINDOWS_DEBIAN_MACOS.md`  
Purpose: execution status for expanded-plan steps 1 and 2.

## Evidence References

- RC release: `https://github.com/edonahue/Discogs_Spinner/releases/tag/v0.2.0-rc4`
- Tagged-release run: `https://github.com/edonahue/Discogs_Spinner/actions/runs/22426315828`
- Post-release validation issue: `https://github.com/edonahue/Discogs_Spinner/issues/1`
- Notes file: `docs/releases/v0.2.0-rc4.md`

## Global Pre-Release Gate

- [x] Working tree is clean and branch is tagged for release candidate.
- [x] `docs/RC_RELEASE_RUNBOOK.md` reviewed for current RC workflow steps.
- [x] `docs/RELEASE_NOTES_TEMPLATE.md` copied and filled for this release.
- [x] `venv/bin/ruff check .` passes.
- [x] `venv/bin/python -m mypy src/discogs_player --show-error-codes --hide-error-context` passes.
- [x] `venv/bin/python -m pytest -q` passes.
- [x] `./scripts/gui_smoke_test.sh 12` passes.
- [x] `./scripts/gallery_ux_smoke.sh 12` passes.
- [x] `LICENSE`, `PRIVACY.md`, `TERMS.md`, `TRADEMARKS.md`, and `COMPLIANCE.md` reviewed.
- [x] No secrets or personal data in commits/artifacts (`.env`, `*.db`, exports, logs).
- [x] Release notes drafted (known limitations + setup steps + support boundaries).

## Stage 1: Windows

### Build and Artifact

- [x] `./scripts/build_artifacts.sh all` produces windows artifacts.
- [x] Artifact names and checksums recorded in release notes.
- [ ] Install path tested on a clean Windows environment.

### FTUX and Functional Checks

- [ ] App launches without CLI prerequisite for normal user flow.
- [ ] First-run setup clearly handles Discogs token setup.
- [ ] Optional Spotify flow reaches auth diagnostics and device listing.
- [ ] `status`, `sync`, `list`, `spin`, `play --open` verified.

### User Acceptance

- [ ] Technical pilot-user path completes without blocker.
- [ ] Non-technical pilot-user path completes with guided instructions only.

## Stage 2: Debian Linux

### Build and Artifact

- [ ] Debian artifact installs on supported distro baseline.
- [x] GUI dependencies and CLI dependencies documented clearly.
- [ ] Launcher integration (if provided) works after install.

### FTUX and Functional Checks

- [x] Discogs-only core profile works end-to-end.
- [ ] Plus profile install (`.[spotify]`) and auth doctor path validated.
- [x] GUI smoke checks pass in target runtime.

## Stage 3: macOS

### Build and Artifact

- [ ] macOS artifact produced and startup tested on clean machine.
- [ ] Gatekeeper behavior documented for current signing/notarization state.
- [ ] Future signing/notarization TODOs captured if release is unsigned.

### FTUX and Functional Checks

- [ ] Onboarding flow and setup messaging are understandable for first-time users.
- [ ] Local data paths and permissions behave as documented.
- [ ] Optional provider actions fail gracefully when unavailable.

## Publish Gate

- [x] GitHub Release created with per-OS asset list and checksums.
- [x] Install docs linked prominently from release notes.
- [x] Issue templates for install/auth/playback are available.
- [x] Post-release validation issue opened to track first-user feedback.

## Post-Release Follow-Up (Within 72 Hours)

- [x] Triage install/auth/playback bug reports.
- [x] Record top friction points in roadmap/backlog docs.
- [ ] Decide go/no-go for widening audience beyond initial pilot-user cohort.

## Notes

- Open install/auth/playback issue count at snapshot time: `0` user-reported (excluding tracking issue `#1`).
- Remaining open items are primarily manual pilot-environment validations and rollout decisioning.
- Debian follow-up pass (2026-02-26 UTC) evidence:
  - Core flow pass on local Debian host: `setup --json`, `sync`, `status --json`, `list --limit 5 --json`, `spin --json`.
  - Plus auth-doctor path pass: `venv/bin/python -m discogs_player.main auth spotify-doctor --json`.
  - GUI smoke pass: `./scripts/gui_smoke_test.sh 12`, `./scripts/gallery_ux_smoke.sh 12`.
- Debian open blockers from the same pass:
  - Clean-venv install from Linux artifacts failed because this shell environment currently cannot resolve package index DNS (`httpx` dependency lookup failed), so clean baseline install remains unchecked.
  - Launcher install wiring works (desktop entry/script/icon created), but launcher runtime smoke under headless sandbox remained unstable (`Gtk couldn't be initialized` in this runtime), so launcher integration remains unchecked pending clean desktop-session validation.
