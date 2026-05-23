# Public Release Checklist: Windows, Debian, macOS

Date created: 2026-02-26  
Owner: Engineering

This checklist is optimized for a public installer release centered on native installs and first-run success across all three operating systems.

## Current Stable Baseline (`v0.2.1`) And Next Packaging Refresh (`v0.2.2`)

- `Installer Build` must be green for the published stable tag and release assets.
- `Windows MSI Smoke` has passed on `main` and is available as the slower Windows confidence lane.
- Remaining non-blocking launch polish: Windows signing, macOS signing/notarization, and first-user feedback triage.
- `v0.2.2` should package the post-`v0.2.1` GTK desktop launch, resize, and gallery cover sizing fixes.

## Global Pre-Release Gate

- [ ] Working tree is clean and branch is tagged for release.
- [ ] [docs/PUBLIC_RELEASE_RUNBOOK.md](PUBLIC_RELEASE_RUNBOOK.md) reviewed for the current installer-release steps.
- [ ] [docs/RELEASE_NOTES_TEMPLATE.md](RELEASE_NOTES_TEMPLATE.md) copied and filled for this release.
- [ ] `venv/bin/ruff check .` passes.
- [ ] `venv/bin/python -m mypy src/discogs_player --show-error-codes --hide-error-context` passes.
- [ ] `venv/bin/python -m pytest -q` passes.
- [ ] `./scripts/gui_smoke_test.sh 12` passes.
- [ ] `./scripts/gallery_ux_smoke.sh 12` passes.
- [ ] `python3 scripts/validate_linux_packaging_metadata.py` passes.
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
- [ ] First-run setup clearly handles Discogs token setup and reaches the token prompt.
- [ ] After a valid Discogs token, first sync reaches the collection view or returns a diagnostic failure that can be filed.
- [ ] Optional Spotify flow reaches auth diagnostics and device listing.
- [ ] `status`, `sync`, `list`, `spin`, `play --open` verified.
- Reference: [docs/validation/windows_tauri_ftux.md](validation/windows_tauri_ftux.md)

### Installer Confidence

- [ ] Clean-machine Windows install path reviewed against [docs/validation/windows_tauri_ftux.md](validation/windows_tauri_ftux.md).
- [ ] SmartScreen guidance in [docs/quickstart_windows.md](quickstart_windows.md) matches the current unsigned/signed posture.

## Stage 2: Debian Linux

### Build and Artifact

- [ ] Debian artifact installs on supported distro baseline.
- [ ] GTK `.deb` includes AppStream metainfo at `/usr/share/metainfo/io.github.edonahue.DiscogsSpinner.metainfo.xml`.
- [ ] `lintian` has run against the GTK `.deb` in CI and any error-level package issues are resolved.
- [ ] Linux Tauri real bundle build passes (`bash ./scripts/validate_tauri_linux_real_build.sh --target-triple x86_64-unknown-linux-gnu` locally or equivalent CI run).
- [ ] Linux Tauri `.deb` and `.AppImage` bundle validation passes and confirms the packaged `dplayer-api` sidecar is present.
- [ ] GUI dependencies and CLI dependencies documented clearly.
- [ ] Launcher integration (if provided) works after install.

### FTUX and Functional Checks

- [ ] Discogs-only core profile works end-to-end.
- [ ] Plus profile install (`.[spotify]`) and auth doctor path validated.
- [ ] GUI smoke checks pass in target runtime.
- Reference: [docs/validation/debian_installer_ftux.md](validation/debian_installer_ftux.md)

## Stage 3: macOS

### Build and Artifact

- [ ] macOS artifact produced and startup tested on clean machine.
- [ ] macOS Tauri installer build passes in CI with real artifact generation (`build-tauri`, not just sidecar contract checks).
- [ ] macOS Tauri bundle validation passes and confirms the packaged `dplayer-api` sidecar is present inside the `.app` bundle shipped in the `.dmg`.
- [ ] Gatekeeper behavior documented for current signing/notarization state.
- [ ] Future signing/notarization TODOs captured if release is unsigned.

### FTUX and Functional Checks

- [ ] Onboarding flow and setup messaging are understandable for first-time users.
- [ ] Launch reaches the setup wizard and Discogs token prompt on a clean profile.
- [ ] After a valid Discogs token, first sync reaches the collection view or returns a diagnostic failure that can be filed.
- [ ] Local data paths and permissions behave as documented.
- [ ] Optional provider actions fail gracefully when unavailable.
- Reference: [docs/validation/macos_installer_ftux.md](validation/macos_installer_ftux.md)

## Publish Gate

- [ ] GitHub Release created with per-OS asset list and checksums.
- [ ] `INSTALLER-MANIFEST.txt` is published next to `CHECKSUMS-INSTALLERS.txt`.
- [ ] README `Download Now` section and OS quickstarts point to the live stable release path.
- [ ] Install docs linked prominently from release notes.
- [ ] Issue templates for install/auth/playback are available.
- [ ] Post-release validation issue opened to track first-user feedback.

## Post-Release Follow-Up (Within 72 Hours)

- [ ] Triage install/auth/playback bug reports.
- [ ] Review friend-trial feedback for download confusion, OS warning confusion, and first-run setup friction.
- [ ] Record top friction points in roadmap/backlog docs.
- [ ] Record any installer friction that should move into the slow Windows MSI smoke lane or signing/notarization backlog.
