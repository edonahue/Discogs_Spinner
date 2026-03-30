# `v1.0.0` Readiness Tracker

Owner: Engineering  
Status: Active  
Purpose: operational tracker for the aspirational `v1.0.0` release target

This file is the execution companion to `docs/RELEASE_TARGET_v1.0.md`.
If a gate below remains open, continue shipping `0.x` releases.

## Current Position

- Product contract for `1.0` is now defined.
- Support matrix for first-class vs secondary surfaces is now defined.
- `v0.2.0` proved cross-platform installer buildability and release publication.
- Remaining `1.0` work is mostly trust, FTUX, and supportability rather than new feature breadth.

## Gate Tracker

| Gate | Status | Evidence / owner notes |
|---|---|---|
| 1.0 product contract documented | done | `docs/RELEASE_TARGET_v1.0.md`, `PRODUCT_STATE.md` |
| Support matrix documented | done | `docs/SUPPORT_MATRIX.md` |
| Windows signing wired and verified | open | See `docs/SIGNING.md`; requires cert + CI secrets |
| macOS signing + notarization wired and verified | open | See `docs/SIGNING.md`; requires Apple Developer credentials |
| Windows clean-machine FTUX recorded | open | Use `docs/validation/windows_tauri_ftux.md` |
| macOS clean-machine FTUX recorded | open | Use `docs/validation/macos_installer_ftux.md` |
| Debian clean-machine FTUX recorded | open | Use `docs/validation/debian_installer_ftux.md` |
| Live timing baseline recorded | open | Record in `docs/STABILIZATION_EXECUTION_2026Q1.md` via `dplayer-gui --timing` |
| Small friend/beta cohort reviewed | open | Use `docs/friend_trial.md` and record top friction items here |
| RC automation and manual gates green | open | `1.0.0-rc1` should only ship after the above gates close |

## Required Evidence Before `1.0.0-rc1`

1. Signed Windows installer artifacts built in CI and validated on a native runner.
2. Signed + notarized macOS artifact built in CI and validated on a clean machine.
3. Clean-machine FTUX notes completed for:
   - Windows
   - macOS
   - Debian/Ubuntu
4. One live timing run recorded with browse-load and wantlist-load latencies.
5. Friend-trial feedback reviewed; any P0/P1 install/setup blockers closed or explicitly accepted.

## Open Questions To Close In This Tracker

- Does widget-population latency require a pre-1.0 optimization pass after the live timing run?
- Are Windows SmartScreen and macOS Gatekeeper issues fully resolved by signing/notarization, or do quickstarts still need fallback notes?
- Does the recommended Linux path remain GTK `.deb`, or should `1.0` elevate a different Linux artifact as the default?

## Exit Rule

Tag `v1.0.0` only when:

- all required gates above are closed,
- no open P0/P1 install/setup/data-loss regressions remain,
- and the release promise in `docs/RELEASE_TARGET_v1.0.md` is actually true in practice.
