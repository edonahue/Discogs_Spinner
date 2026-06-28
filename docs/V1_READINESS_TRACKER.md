# `v1.0.0` Readiness Tracker

Owner: Engineering  
Status: Active  
Purpose: operational tracker for the aspirational `v1.0.0` release target

This file is the execution companion to `docs/RELEASE_TARGET_v1.0.md`.
If a gate below remains open, continue shipping `0.x` releases.

For the end-to-end ordered path (which doc to use at each step), see
**`docs/V1_RELEASE_FLOW.md`**. The per-OS validation gate lives in
**`docs/RELEASE_CHECKLIST_WINDOWS_DEBIAN_MACOS.md`**.

## Current Position

- Product contract for `1.0` is now defined.
- Support matrix for first-class vs secondary surfaces is now defined.
- `v0.2.0` proved cross-platform installer buildability and release publication.
- CI now enforces lint, type checking, the full Python test suite, and webapp
  lint/type/tests on every push (closed below).
- Remaining `1.0` work is mostly trust, FTUX, and supportability rather than new feature breadth.

## Gate Tracker

| Gate | Status | Evidence / owner notes |
|---|---|---|
| 1.0 product contract documented | done | `docs/RELEASE_TARGET_v1.0.md`, `PRODUCT_STATE.md` |
| Support matrix documented | done | `docs/SUPPORT_MATRIX.md` |
| CI quality gates (lint, type check, full test suite) | done | `.github/workflows/core_plus_ci.yml` — `lint` (ruff + mypy), `test-full`, and `webapp-lint` (eslint + tsc + prettier + vitest) jobs; added in PRs #26, #29, #31 |
| Signing CI wiring exists | done | `installer_build.yml` "Configure optional code-signing env" + keychain import steps consume the signing secrets; builds unsigned without them, signed with them |
| Windows signing secrets set + signed build verified | open | Set `WINDOWS_CERTIFICATE*` secrets per `docs/SIGNING.md`, then verify a signed `-setup.exe` |
| macOS signing + notarization secrets set + verified | open | Set `APPLE_*` secrets per `docs/SIGNING.md` (requires Apple Developer Program); verify with `spctl --assess` |
| Windows clean-machine FTUX recorded | open | Use `docs/validation/windows_tauri_ftux.md` |
| macOS clean-machine FTUX recorded | open | Use `docs/validation/macos_installer_ftux.md` |
| Debian clean-machine FTUX recorded | open | Use `docs/validation/debian_installer_ftux.md` |
| Live timing baseline recorded | open | Record in `docs/STABILIZATION_EXECUTION_2026Q1.md` via `dplayer-gui --timing` |
| Small friend/beta cohort reviewed | open | Use `docs/friend_trial.md`; log friction in the table below |
| RC automation and manual gates green | open | `1.0.0-rc1` should only ship after the above gates close; cut via `docs/PUBLIC_RELEASE_RUNBOOK.md` |

## Required Evidence Before `1.0.0-rc1`

1. Signed Windows installer artifacts built in CI and validated on a native runner.
2. Signed + notarized macOS artifact built in CI and validated on a clean machine.
3. Clean-machine FTUX notes completed for:
   - Windows
   - macOS
   - Debian/Ubuntu
4. One live timing run recorded with browse-load and wantlist-load latencies.
5. Friend-trial feedback reviewed; any P0/P1 install/setup blockers closed or explicitly accepted.

## Friend-Trial Friction Log

Record top friction items from the friend/beta cohort here (see `docs/friend_trial.md`).
Severity: P0 = blocks install/setup, P1 = major friction, P2 = polish. Resolution:
fixed (PR/issue link), accepted (known limitation), or open.

| Date | OS | Reporter | Friction item | Severity | Resolution |
|---|---|---|---|---|---|
| _(none recorded yet)_ | | | | | |

## Open Questions To Close In This Tracker

- Does widget-population latency require a pre-1.0 optimization pass after the live timing run?
- Are Windows SmartScreen and macOS Gatekeeper issues fully resolved by signing/notarization, or do quickstarts still need fallback notes?
- Does the recommended Linux path remain GTK `.deb`, or should `1.0` elevate a different Linux artifact as the default?

## Exit Rule

Tag `v1.0.0` only when:

- all required gates above are closed,
- no open P0/P1 install/setup/data-loss regressions remain,
- and the release promise in `docs/RELEASE_TARGET_v1.0.md` is actually true in practice.
