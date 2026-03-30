# Release Checklist: Windows -> Debian -> macOS

Date created: 2026-02-26  
Owner: Engineering

This checklist is optimized for the staged rollout order agreed in strategic planning:

1. Windows
2. Debian Linux
3. macOS

## Global Pre-Release Gate

- [ ] Working tree is clean and branch is tagged for release candidate.
- [ ] `docs/RC_RELEASE_RUNBOOK.md` reviewed for current RC workflow steps.
- [ ] `docs/RELEASE_NOTES_TEMPLATE.md` copied and filled for this release.
- [ ] `venv/bin/ruff check .` passes.
- [ ] `venv/bin/python -m mypy src/discogs_player --show-error-codes --hide-error-context` passes.
- [ ] `venv/bin/python -m pytest -q` passes.
- [ ] `./scripts/gui_smoke_test.sh 12` passes.
- [ ] `./scripts/gallery_ux_smoke.sh 12` passes.
- [ ] `LICENSE`, `PRIVACY.md`, `TERMS.md`, `TRADEMARKS.md`, and `COMPLIANCE.md` reviewed.
- [ ] No secrets or personal data in commits/artifacts (`.env`, `*.db`, exports, logs).
- [ ] Release notes drafted (known limitations + setup steps + support boundaries).

## Stage 1: Windows

### Build and Artifact

- [ ] `./scripts/build_artifacts.sh all` produces windows artifacts.
- [ ] Windows Tauri installer build passes in CI with real artifact generation (`build-tauri`, not just sidecar contract checks).
- [ ] Windows Tauri bundle validation passes and confirms the packaged `dplayer-api.exe` sidecar is present in both `.msi` and NSIS installers.
- [ ] Artifact names and checksums recorded in release notes.
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
- [ ] Linux Tauri real bundle build passes (`bash ./scripts/validate_tauri_linux_real_build.sh --target-triple x86_64-unknown-linux-gnu` locally or equivalent CI run).
- [ ] Linux Tauri `.deb` and `.AppImage` bundle validation passes and confirms the packaged `dplayer-api` sidecar is present.
- [ ] GUI dependencies and CLI dependencies documented clearly.
- [ ] Launcher integration (if provided) works after install.

### FTUX and Functional Checks

- [ ] Discogs-only core profile works end-to-end.
- [ ] Plus profile install (`.[spotify]`) and auth doctor path validated.
- [ ] GUI smoke checks pass in target runtime.

## Stage 3: macOS

### Build and Artifact

- [ ] macOS artifact produced and startup tested on clean machine.
- [ ] macOS Tauri installer build passes in CI with real artifact generation (`build-tauri`, not just sidecar contract checks).
- [ ] macOS Tauri bundle validation passes and confirms the packaged `dplayer-api` sidecar is present inside the `.app` bundle shipped in the `.dmg`.
- [ ] Gatekeeper behavior documented for current signing/notarization state.
- [ ] Future signing/notarization TODOs captured if release is unsigned.

### FTUX and Functional Checks

- [ ] Onboarding flow and setup messaging are understandable for first-time users.
- [ ] Local data paths and permissions behave as documented.
- [ ] Optional provider actions fail gracefully when unavailable.

## Publish Gate

- [ ] GitHub Release created with per-OS asset list and checksums.
- [ ] Install docs linked prominently from release notes.
- [ ] Issue templates for install/auth/playback are available.
- [ ] Post-release validation issue opened to track first-user feedback.

## Post-Release Follow-Up (Within 72 Hours)

- [ ] Triage install/auth/playback bug reports.
- [ ] Record top friction points in roadmap/backlog docs.
- [ ] Decide go/no-go for widening audience beyond initial pilot-user cohort.
