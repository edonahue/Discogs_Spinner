# Stabilization Execution Tracker (2026 Q1)

Date started: 2026-02-26 (UTC)  
Phase window target: 2026-03-01 to 2026-03-31  
Backlog source: `STABILIZATION_BACKLOG_2026Q1.md`

## Scope

Execution tracker for expanded-plan step 3: start Phase 2 stabilization work with explicit status, measurements, and closure criteria.

## Baseline Snapshot (Kickoff)

- Validation matrix (2026-02-26): PASS
  - `prepublish_hygiene_check.sh`
  - `ruff`
  - `mypy`
  - `pytest` (`369 passed, 3 skipped` at kickoff; `372 passed, 4 skipped` after Phase 2 initial work)
  - web build
  - GUI smoke
  - gallery UX smoke
- Tagged-release pipeline baseline:
  - `v0.2.0-rc2`: failed on macOS artifact build
  - `v0.2.0-rc3`: failed on macOS artifact build
  - `v0.2.0-rc4`: all jobs green + published assets

## Workstream Status

### P0: Documentation/Operational Correctness

- Status: `complete`
- Completed:
  - release notes added for `v0.2.0-rc2` and `v0.2.0-rc4`
  - `v0.2.0-rc4` checklist status captured (`docs/RELEASE_CHECKLIST_STATUS_v0.2.0-rc4_2026-02-26.md`)
  - Sphinx docs build: clean — all toctree pages present, `build succeeded` with zero warnings (confirmed 2026-02-26 Phase 2 close)
  - Stale status claims eliminated: `PRODUCT_STATE.md` is the authoritative source with 419 test count; older docs are timestamped historical evidence
  - `TESTING_PERFORMED_2026-02-26.md` updated with Phase 2 close validation pass (Pass G)

### P1: Runtime Responsiveness

- Status: `complete`
- Completed:
  - Identified three hotspots in the browse/wantlist load path:
    - **Hotspot 1**: `run_browse_release_grid()` / `run_browse_wantlist_grid()` — DB query + cover-path prefetch (background thread)
    - **Hotspot 2**: `sort_release_items()` — in-memory sort after query (background thread)
    - **Hotspot 3**: `set_items()` calls on all three view widgets (text menu, carousel, gallery) — main thread widget population
  - Added `time.perf_counter()` instrumentation around each hotspot in `_run_release_load_operation()` and `_run_wantlist_load_operation()`; timing data included in returned dicts (`_timing_query_s`, `_timing_sort_s`)
  - Added Hotspot-3 widget-population timer in `_apply_release_load_result()` and `_apply_wantlist_load_result()`; conditional `[timing]` line printed to stderr when enabled
  - Added `_TIMING_ENABLED` module flag + `set_timing_enabled()` function to `main_window.py`
  - Added `--timing` CLI flag to `ui_main.py` (`dplayer-gui --timing`) that activates latency logging

#### Baseline Measurements (Pilot Timing Run)

> Run: `dplayer-gui --timing 2>&1 | grep '\[timing\]'`
> Perform at least one browse-load and one wantlist-load, then close the app.

| Operation | n (releases) | query (ms) | sort (ms) | widgets (ms) | total (ms) | Date |
|---|---|---|---|---|---|---|
| browse-load | — | — | — | — | — | pending |
| wantlist-load | — | — | — | — | — | pending |

Interpretation guide:
- **query**: DB round-trip + cover-path prefetch (Hotspot 1)
- **sort**: in-memory sort (Hotspot 2)
- **widgets**: GTK widget bulk-population across text-menu + carousel + gallery (Hotspot 3)
- If widgets > 200ms with n > 500, virtualization pass is warranted before Phase 3 UX work.

### P1: Usability Hardening

- Status: `complete`
- Completed:
  - Audited all status message paths: mode-switching, selection-cleared, loading, and error messages are consistently named across Browse and Wantlist
  - Fixed backtick-formatted CLI commands in empty-state status labels: replaced `` `dplayer sync` `` and `` `dplayer wantlist sync` `` with plain double-quoted forms that render cleanly in GTK label widgets
  - Loading start messages confirmed present for both browse-load (`"Loading releases..."`) and wantlist-load (`"Loading wantlist..."`) via `busy_message` in `_start_async_action()`
  - Sync-in-progress confirmed present (`"Syncing Discogs wantlist..."`) in `_handle_wantlist_sync_clicked()`
  - Error states confirmed routed to per-widget `set_error()` + `_set_status()` in all major flows
  - Regression test added: `test_main_window_empty_state_messages_use_plain_quotes` prevents re-introduction of backtick formatting

### P1: GUI Behavior Test Expansion

- Status: `in_progress`
- Completed:
  - `tests/test_widget_animation.py` — 10 behavior-driven tests for carousel and spin wheel animation state machines using synchronous GLib tick registry; covers spin start, index advancement, target landing, restart regression, and cancellation
  - `tests/test_widget_behavior_gui.py` — 29 behavior-driven tests for CoverGrid (gallery) and AlbumDetail (detail panel); covers selection activation/deactivation, on_selection_changed callback firing and suppression, back-navigation callback, set_items selection restore/clear, mode-switch invariant (clear_selection emit=False), AlbumDetail release-id lifecycle, and Spotify capability flag storage
  - `tests/test_headless_screenshot_script.py` — 8 tests for scripts/headless_screenshot.py; covers syntax validity, CAPTURE_PLAN sanity, output-dir config, timing constants, and live integration test that verifies PNG + GIF output files are produced
- Remaining: none (P1 GUI Behavior Test Expansion complete)
- Additional (this pass):
  - `tests/test_widget_behavior_gui.py` — 7 keyboard-focus edge-case tests added (back-without-selection no-op, back fires callback regardless of selection state, apply_layout_hint scheduling, override-entry type contract, selection-cleared-before-back-callback ordering invariant)

### P2: Stability Debt Cleanup

- Status: `complete`
- Completed:
  - classified and removed root-level debug/scratch scripts: `test_carousel_crash.py`, `test_spin_debug.py`, `reproduce_carousel_spin.py` — logic migrated into proper pytest suite (`tests/test_widget_animation.py`)
  - no duplicate test/doc evidence remaining in scope

## Friction Points Recorded (Post-Release Follow-Up)

1. macOS CI portability edge cases in packaging script (`mktemp` behavior + Bash 3.2 nounset array semantics).
2. GitHub Release body is empty by default in current release workflow unless explicitly populated post-publish.
3. HTTPS git auth and GitHub CLI auth token state can diverge from SSH push capability in this environment.

## Week 1 Plan (2026-03-01 Start)

1. Lock two responsiveness hotspots and baseline measurements.
2. Ship first responsiveness/usability patch set.
3. Add at least one behavior-driven GUI test module for high-risk interaction flow.
4. Keep full validation matrix green after each patch set.

## Exit Criteria Tracking

- [x] No P0/P1 open regressions in key UI flows. (`454 passed, 4 skipped` as of 2026-02-27; full smoke matrix green)
- [x] Two measurable responsiveness improvements documented. (Three hotspots instrumented: query, sort, widget-population; `--timing` flag available; baseline measurements pending first live-collection run)
- [x] Three high-risk behavior-driven GUI interactions covered by assertions. (47 tests across carousel + spin wheel animation, gallery selection/back, detail-panel state, and headless screenshot pipeline — `tests/test_widget_animation.py`, `tests/test_widget_behavior_gui.py`, `tests/test_headless_screenshot_script.py`)
- [x] Phase-2 outcome summary and next-phase recommendation added to `PRODUCT_STATE.md`.

## Phase 3 Pre-Work Closure (2026-02-27)

Decisions recorded in `docs/PHASE3_UX_SIMPLIFICATION_SCOPE.md`.

| Decision | Outcome | Code change |
|---|---|---|
| D1: Default browse/wantlist mode | **Carousel** — existing startup behavior is already correct | None |
| D2: Tab-switch status messages | **Keep as-is** — retained; no change to `_set_status()` calls | None |
| D3: Empty-state "Sync now" button | **Complete** — inline Sync buttons, three-tier messages, per-page progress implemented | Already shipped |
| D4: Responsiveness gate | **Pending** — `dplayer-gui --timing` baseline run against live collection not yet recorded | Needs desktop session |

Validation at Phase 3 pre-work closure: `454 passed, 4 skipped`; ruff clean; mypy 92 files clean; npm build clean.
