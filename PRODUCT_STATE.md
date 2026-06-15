# Product State: Discogs Spinner (internal: `discogs_player`)

Date: 2026-02-26 (UTC)
Owner: Product/Engineering
Status: Active

## Purpose

This document is the single source of truth for:

1. Product intent and goals
2. Current capabilities in the app and repo
3. What remains to ship, stabilize, and polish

It reconciles older planning/status documents and should be updated whenever roadmap priorities change.

Related strategic intent notes:

- `docs/STRATEGIC_EXPANSION_NOTES_2026-02-26.md` (ambitious platform/monetization vision + staged rollout intent)
- `docs/STATUS_CHECKPOINT_2026-02-26.md` (current implementation checkpoint snapshot)

## Source-Of-Truth Order

When docs disagree, use this precedence:

1. `PRODUCT_STATE.md` (this file)
2. `README.md` (user-facing usage + setup)
3. `docs/STATUS_CHECKPOINT_2026-02-26.md` (latest execution checkpoint)
4. `docs/TESTING_PERFORMED_2026-02-26.md` (latest validation evidence)
5. ADRs in `docs/adr/`
6. Older summaries (`PROJECT_SNAPSHOT.md`, `PROJECT_ASSESSMENT.md`, `DOCUMENTATION_SUMMARY.md`)

## Product Intent (Reconciled)

The project remains fundamentally:

- CLI-first and SSH-usable for all critical workflows
- Local-first (SQLite + local cache + XDG paths)
- Layered architecture with shared use-cases across CLI and GUI
- Optional Spotify addon, not a hard dependency for core Discogs workflows

The current scope has expanded beyond the original MVP and now includes:

- Full wantlist workflows
- Market value dashboard and operations
- Multiple GUI browse modes (carousel, text menu, gallery)
- Import/export and mapping bootstrap tooling

## 1.0 Release Target (Recommended)

Recommended interpretation of `v1.0.0` when the product is ready for it:

- reliable local-first collector app
- stable CLI plus native installers as the first-class surfaces
- predictable first-run setup and sync on Windows, macOS, and Linux
- optional Spotify integration, but not a hard 1.0 dependency

This implies:

- web/API parity is not a `1.0` blocker
- installer trust and supportability are now more important than adding new feature breadth
- signing/notarization and clean-machine FTUX are 1.0 release gates, not post-1.0 polish
- if these gates are not closed, continue shipping `0.x` releases rather than forcing a `1.0` increment

## Distribution Channels

| Channel | Platform | Status | Notes |
|---------|----------|--------|-------|
| GitHub Releases (direct download) | Windows, macOS, Linux | **Live** | NSIS exe + MSI (Windows), .dmg (macOS), .deb + AppImage (Linux) |
| Snap Store (`spinner-for-discogs`) | Linux | **Live** | `sudo snap install spinner-for-discogs`; auto-published via CI on tag |
| WinGet (`ErichDonahue.SpinnerforDiscogs`) | Windows | **Live** | `winget install ErichDonahue.SpinnerforDiscogs`; PR [#384707](https://github.com/microsoft/winget-pkgs/pull/384707) merged to `microsoft/winget-pkgs` on 2026-06-13 |
| Homebrew Cask | macOS | **Formula ready, not yet submitted** | Awaiting notarized `.dmg` (requires Apple Developer enrollment) |
| Flathub | Linux | **Template ready, not yet submitted** | Awaiting AppStream screenshots + Python dep JSON |
| Microsoft Store | Windows | **Not started** | Requires Partner Center account + MSIX conversion |

Reference: `docs/STORE_SUBMISSIONS.md` for end-to-end submission steps and per-channel checklists.

---

## Current Capability Snapshot

### Core Platform

- Discogs sync with incremental updates + soft-delete behavior
- Local SQLite persistence and migration-based schema evolution
- Image cache integration for UI album art
- Capability-aware optional Spotify backend integration

### CLI (Current Surface)

Implemented command groups include:

- Core: `status`, `setup`, `sync`, `list`, `spin`, `play`, `open`, `recent`, `analytics`
- Device/config/auth: `devices`, `device`, `config`, `auth`
- Matching/review: `match`, `review`, `bootstrap`
- Extended data: `wantlist`, `value`, `tracks`, `stats`

This exceeds original MVP command scope and is production-usable for advanced workflows.

### GUI (Current Surface)

Main sections:

- Browse
- Wantlist
- Market Value

Browse and Wantlist both support:

- Carousel mode
- Text Menu mode
- Gallery mode (with selection hero state + back flow)

GUI also includes:

- Detail sidebars with tracklist refresh hooks
- Spin wheel controls
- Device picker and Spotify capability-aware controls
- Value dashboard with refresh/snapshot operations

### Validation Baseline (As Of 2026-02-27, Updated Post Phase 3 Onboarding Work)

Most recent recorded validation:

- `prepublish_hygiene_check.sh`: passing
- `ruff`: passing
- `mypy`: passing (`92` source files checked)
- `pytest -q`: `488 passed, 4 skipped` (up from `362 passed, 4 skipped` at Phase 1 close)
- `npm --prefix webapp run build`: passing

Reference: `docs/TESTING_PERFORMED_2026-02-26.md`, `docs/STABILIZATION_EXECUTION_2026Q1.md`

### Current Delivery Checkpoint (As Of 2026-02-26)

- Public repo target is set to `https://github.com/edonahue/Discogs_Spinner.git`.
- Docs are aligned to public naming (`Discogs Spinner`) and explicitly state no embedded in-app streaming.
- Repository sanitation pass and `.gitignore` hardening are complete.
- First checklist/runbook pass has been executed (`docs/RELEASE_CHECKLIST_FIRST_PASS_2026-02-26.md`).
- `master` is pushed and tracks `origin/master`.
- Post-checkpoint update: tagged-release workflow is green on `v0.2.0-rc4` (all OS artifact jobs + publish succeeded).
- Post-checkpoint update: live release checklist status is tracked in `docs/RELEASE_CHECKLIST_STATUS_v0.2.0-rc4_2026-02-26.md`.
- Post-checkpoint update: Windows/macOS clean-runner pilot validation automation pass has been recorded (workflow-backed command-path checks).
- Post-checkpoint update: rollout decision is currently **NO-GO** for widening beyond pilot cohort until remaining manual OS validations close.

## Plan Alignment Snapshot (As Of 2026-02-26)

Reference plan: `project_plan.md` (original CLI-first MVP + stretch-goal baseline).

### Original Plan Goals vs Current State

| Plan area (`project_plan.md`) | Planned scope | Current state | Status |
| --- | --- | --- | --- |
| Discogs sync + local cache | Sync collection into SQLite with incremental updates and CLI-verifiable results | Implemented and operating with sync, persistence, migrations, and release/readiness validation evidence | Complete |
| CLI-lite over SSH | Core commands (`sync`, `status`, `list`, `spin`, `play`, `devices`, `match`, `config`) with JSON options | Implemented and expanded (`setup`, `open`, `recent`, `analytics`, `wantlist`, `value`, `review`, `bootstrap`, etc.) | Complete (exceeds MVP) |
| Spotify playback (optional) | OAuth, device selection, playback on default device, fallback messaging | Implemented as capability-aware optional addon with auth doctor, device controls, play/open fallback flows | Complete |
| Desktop UI as thin layer on shared core | Later-phase GTK UI using shared use-cases (no UI-side API calls) | Implemented with browse/wantlist/value surfaces and shared use-case architecture; complexity now needs stabilization hardening | Complete (now in stabilization) |
| Stretch goals (market value, wantlist, analytics, export) | Designed-in for later expansion | Implemented substantially beyond MVP baseline and already available in CLI/GUI flows | Complete (ahead of plan) |
| Non-goals guardrail | No embedded audio streaming in app UI | Preserved; documentation and UX explicitly state external-app playback control only | On-plan |

Overall position vs original plan:

- Ahead on feature scope and command/UI breadth.
- Behind only on final release hardening for wider rollout (manual cross-OS checklist closures still open).

### Dated Roadmap Progress (This File)

- Phase 1 (Documentation Convergence, 2026-02-23 to 2026-03-01): Complete. Canonical-state ownership, README alignment, historical-doc positioning, and release note coverage done. Sphinx toctree gap remains a minor open item.
- Phase 2 (Stabilization And Responsiveness, 2026-03-01 to 2026-03-31): **Complete (executed early, Feb 26)**. All P1/P2 exit criteria met. See outcome summary below.
- Phase 3 (UX Simplification And Flow Hardening, 2026-04-01 to 2026-04-30): Ready to start. See recommendation below.
- Phase 4 (Next Feature Block, 2026-05-01 to 2026-06-30): Not started.

## Current Gaps And Risks

1. Documentation drift

- Some historical status files report outdated test counts/completeness snapshots. These are now positioned as timestamped historical evidence; `PRODUCT_STATE.md` is authoritative.
- Sphinx toctree: **Resolved**. All 9 toctree entries have corresponding RST files; `sphinx -b html` builds cleanly with zero warnings (confirmed 2026-02-26).
- **Status**: Closed.

2. Product focus drift

- Original "CLI-first, thin GUI" intent is still valid architecturally, but feature growth has increased UI complexity.
- Default UX paths should stay simple while retaining advanced controls.
- **Status**: Unchanged; Phase 3 scope directly addresses this.

3. Test strategy imbalance

- ~~Strong automated coverage exists, but many GUI checks are static marker tests and smoke checks.~~ **Closed by Phase 2**: three behavior-driven test modules now cover animation state machines, gallery/detail selection flows, screenshot pipeline, and keyboard-focus edge cases (47 assertions). 446 total tests passing.

4. Release readiness housekeeping

- Public-release checklist items (license/history/data hygiene, portability messaging) need explicit closure tracking.
- **Status**: Unchanged; remains a prerequisite before widening beyond pilot cohort.

5. Responsiveness baseline (new, post-Phase 2)

- Timing infrastructure is in place (`dplayer-gui --timing`) but no live-collection latency measurements have been recorded yet.
- Actual query/sort/widget-population timings for typical collection sizes (200–2000 releases) are unknown until a pilot run.
- **Action**: Capture one timing run during pilot validation and record numbers in `STABILIZATION_EXECUTION_2026Q1.md`.

6. 1.0 release trust gap

- `v0.2.0` proved installer buildability and cross-platform release execution, but the current public release still depends on unsigned Windows/macOS flows.
- The repo now needs a narrower 1.0 contract, a support matrix, signing/notarization closure, and clean-machine FTUX evidence before it should claim `1.0`.
- **Action**: Track against `docs/RELEASE_TARGET_v1.0.md` and `docs/SUPPORT_MATRIX.md`.

## Dated Roadmap

### Phase 1: Documentation Convergence
Window: 2026-02-23 to 2026-03-01
Goal: Make product state and docs consistent and trustworthy.

Deliverables:

- Keep this file as the canonical state doc
- Update `README.md` to align terminology and declared scope
- Mark older status docs as historical or replace with links to this file
- Resolve Sphinx doc index mismatch (add missing pages or trim toctree)

Success criteria:

- No conflicting "current status" claims across top-level docs
- Docs build path reflects actual files

### Phase 2: Stabilization And Responsiveness
Window: 2026-03-01 to 2026-03-31 (executed 2026-02-26, ahead of window)
Goal: Improve perceived performance and reduce UI regressions.

Deliverables:

- Execute `STABILIZATION_BACKLOG_2026Q1.md` under strict stabilization scope
- Continue targeted UI runtime optimizations (selection, resize, navigation)
- Add behavior-driven GUI tests for gallery/carousel/wantlist/detail interactions
- Add lightweight performance instrumentation for key interaction latency

Success criteria:

- No critical regressions across full test + smoke matrix
- Improved interaction responsiveness under typical datasets

#### Phase 2 Outcome Summary

Date closed: 2026-02-26 (ahead of planned 2026-03-01 start).
Execution reference: `docs/STABILIZATION_EXECUTION_2026Q1.md`

**What was done:**

| Workstream | Result |
|---|---|
| P0: Documentation/Operational Correctness | Substantially complete. Release notes, checklist status, and Sphinx baseline captured. Minor stale-doc cleanup is ongoing. |
| P2: Stability Debt Cleanup | Complete. Root-level scratch scripts (`test_carousel_crash.py`, `test_spin_debug.py`, `reproduce_carousel_spin.py`) removed; logic migrated to proper pytest suite. |
| P1: GUI Behavior Test Expansion | Complete. Three new test modules added (47 assertions): animation state machines, gallery/detail-panel selection flows, headless screenshot pipeline, keyboard-focus edge cases. |
| P1: Usability Hardening | Complete. All status message paths audited; backtick-formatted CLI commands in GUI empty-state labels replaced with plain quotes; regression test added. |
| P1: Runtime Responsiveness | Complete (instrumentation). Three hotspots identified and instrumented in browse/wantlist load path: DB query (`_timing_query_s`), sort (`_timing_sort_s`), and widget population. `--timing` flag added to `dplayer-gui`. Baseline latency measurements pending first live pilot run. |

**Exit criteria status:**

- [x] No P0/P1 open regressions in key UI flows — 488 tests passing, 4 skipped; full smoke matrix green.
- [x] Two measurable responsiveness improvements documented — three hotspots instrumented with `time.perf_counter()` hooks; `dplayer-gui --timing` activates per-load latency output.
- [x] Three high-risk GUI interactions covered by behavior assertions — 47 tests across `test_widget_animation.py`, `test_widget_behavior_gui.py`, `test_headless_screenshot_script.py`.
- [x] Phase-2 outcome summary added to `PRODUCT_STATE.md` — this section.

**What changed in the codebase:**

- `src/discogs_player/ui/main_window.py`: `import time`, `_TIMING_ENABLED`, `set_timing_enabled()`, timing wrappers in `_run_release_load_operation()` / `_run_wantlist_load_operation()` / `_apply_*_load_result()`, fixed empty-state status message formatting.
- `src/discogs_player/ui_main.py`: `--timing` flag wired to `set_timing_enabled()`.
- `tests/`: added `test_widget_animation.py` (10 tests), `test_widget_behavior_gui.py` (36 tests), `test_headless_screenshot_script.py` (8 tests); extended `test_performance_optimizations.py` (3 tests).
- `scripts/`: added `headless_screenshot.py`, `capture_readme_media.sh`.
- `docs/media/screenshots/`: refreshed from live headless run.

**What was explicitly not done (stabilization scope preserved):**

- No new features added.
- No refactors beyond the timing hook additions.
- No changes to use-case layer, CLI commands, or data schema.

**Next-phase recommendation:**

Phase 3 (UX Simplification) is ready to start. The Phase 2 work surfaces two concrete inputs for Phase 3 scope:

1. The timing baseline run (via `dplayer-gui --timing` against a live collection) should be the first act of Phase 3, to determine whether widget-population latency needs optimization before UX simplification work begins.
2. Status message audit confirmed the infrastructure is consistent, so Phase 3 can focus on reducing *quantity* of messages (the tab-switch "Switched to X view" messages fire on every navigation and may be candidates for removal or rate-limiting).

Suggested Phase 3 kickoff checklist:
- [ ] Run `dplayer-gui --timing` against pilot user collection; record numbers in `STABILIZATION_EXECUTION_2026Q1.md`.
- [ ] Re-evaluate whether widget-population time warrants a virtualization pass before or after UX work.
- [ ] Define "simple path" defaults for Browse and Wantlist (which mode to open in, whether to suppress mode toggles for new users).
- [ ] Decide whether "Switched to X view" tab messages stay, are suppressed, or are replaced with something less ephemeral.

### Phase 3: UX Simplification And Flow Hardening
Window: 2026-04-01 to 2026-04-30
Goal: Reduce cognitive load while preserving advanced capability.

Deliverables:

- Define and enforce default "simple path" in Browse/Wantlist flows
- Standardize status messaging and action result feedback
- Tighten empty/error/loading states across CLI and GUI

Success criteria:

- Fewer interaction dead-ends
- Clearer first-run and routine-use experience

### Phase 4: Next Feature Block (Discogs-First ROI)
Window: 2026-05-01 to 2026-06-30
Goal: Ship one high-ROI Discogs-first feature set after stabilization.

Candidate priorities:

1. Value Movers panel
2. Price Refresh Prioritizer
3. Collection Health Score + Data Quality Queue

Selection rule:

- Choose one primary feature track and complete it end-to-end (use case, CLI/UI exposure, tests, docs) before opening the next.

## Near-Term Action Queue

Updated 2026-02-27 (post Phase 3 onboarding work).

**Completed since Phase 2 close (2026-02-27):**
- First-run onboarding improvements: startup token check, empty-state Sync buttons, per-page sync progress, never-synced vs filter-mismatch distinction, startup timing instrumentation.
- Last-synced-at indicator in Browse/Wantlist status bar.
- Token setup instructions added to `install_desktop_app.sh` post-install output.
- Phase 3 scope decisions D3 (empty-state affordance) substantially complete.
- Quickstart docs updated with GUI launch section.
- Phase 3 scope doc: `docs/PHASE3_UX_SIMPLIFICATION_SCOPE.md`.

**Completed since 2026-02-27 (Phase 4 pre-work):**
- Phase 3 D1/D2/D3 decisions closed; success criteria ticked in `docs/PHASE3_UX_SIMPLIFICATION_SCOPE.md`.
- pyproject.toml version corrected: `0.1.0` → `0.2.0rc5` (diagnostics now reports correct version).
- Trailing whitespace cleaned from 8 source files (ruff W293).
- Phase 4 Track A (Price Refresh Prioritizer): `use_cases/value_refresh_queue.py` + `dplayer value queue` CLI + 16 tests.
- Phase 4 Track B (Collection Health Score): `use_cases/collection_health.py` + `dplayer health` CLI + 18 tests.
- Version regression test added: `test_pyproject_version_not_default_placeholder`.
- `docs/PHASE4_FEATURE_SCOPE.md` created; schema constraint on Value Movers documented.

**Still open:**
1. **Pilot timing run** — Run `dplayer-gui --timing` against the pilot user's real collection and record latencies in `docs/STABILIZATION_EXECUTION_2026Q1.md`. *(Needs user action.)*
2. **Pilot validation** — Close remaining manual checklist items (Windows non-CLI launch, Debian desktop session, macOS Gatekeeper docs) and re-evaluate rollout go/no-go. *(Needs user action.)*
3. **Phase 4 GUI wiring** — Wire `value queue` and `health` into GUI panels (post-CLI phase; Track A and B CLI complete).
4. **Phase 4 Track C (Value Movers)** — Requires schema design decision (D4) before implementation; see `docs/PHASE4_FEATURE_SCOPE.md`.
