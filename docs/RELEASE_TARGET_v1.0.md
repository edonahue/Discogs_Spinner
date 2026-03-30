# Release Target: `v1.0.0`

This document defines what `1.0` means for Discogs Spinner when the product is ready for it.
It is an aspirational release target, not a commitment that the next tag must be `1.0.0`.

Operational tracking lives in `docs/V1_READINESS_TRACKER.md`.

## 1.0 Promise

`v1.0.0` should only ship once Discogs Spinner is a **reliable local-first collector app** with:

- a stable CLI (`dplayer`)
- dependable native installers on Windows, macOS, and Linux
- predictable first-run setup for Discogs token entry and first sync
- clear support boundaries and reporting paths

In short: `1.0` means **stable CLI plus native installers** with a release bar high enough that normal users can trust the default OS install path.

For `1.0`, the first-class surfaces are:

- CLI
- native desktop installers

The following remain secondary for `1.0`:

- web/API parity
- advanced automation extras
- experimental or platform-specific edge workflows

That means **web/API parity is not a `1.0` blocker**.

## 1.0 Required Gates

The following must be true before tagging `v1.0.0`:

1. Product contract is documented and consistent across:
   - `PRODUCT_STATE.md`
   - `README.md`
   - release notes
   - support/install docs
2. Recommended installer per OS is explicit:
   - Windows: NSIS `-setup.exe`
   - macOS: `.dmg`
   - Debian/Ubuntu: GTK `.deb`
3. Signing trust is raised to a 1.0 bar:
   - Windows and macOS installers are signed
   - macOS app is also notarized
4. Release validation is green:
   - full lint/type/test baseline
   - `Installer Build`
   - `Windows MSI Smoke`
5. Manual clean-machine FTUX is completed on:
   - Windows
   - macOS
   - Debian/Ubuntu
6. One live timing baseline is captured with `dplayer-gui --timing` against a real collection and recorded in `docs/STABILIZATION_EXECUTION_2026Q1.md`.
7. A small friend/beta cohort has exercised download, install, first launch, and setup; top friction items are fixed or explicitly accepted as known limitations.

## Acceptance Criteria

A new user on each supported OS should be able to:

1. choose the correct installer without guessing
2. install and launch the app
3. enter a Discogs token
4. complete first sync
5. browse or spin without a crash or blank state
6. understand how to report a problem if something fails

## Explicit Non-Goals For `1.0`

These are valuable, but not required for `v1.0.0`:

- full web/API parity with native surfaces
- new feature-track expansion beyond the current collector workflows
- Windows Task Scheduler or other platform-specific automation add-ons
- marketplace notification features

## Release Shape

Recommended path once the readiness bar is actually met:

1. close the signing/notarization work
2. run a `1.0.0-rc1`
3. validate automated matrix + manual FTUX + friend trial
4. fix remaining P0/P1 release blockers only
5. tag `v1.0.0`
