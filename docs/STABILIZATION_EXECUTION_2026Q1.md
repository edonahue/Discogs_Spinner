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

- Status: `in_progress`
- Completed:
  - release notes added for `v0.2.0-rc2` and `v0.2.0-rc4`
  - `v0.2.0-rc4` checklist status captured (`docs/RELEASE_CHECKLIST_STATUS_v0.2.0-rc4_2026-02-26.md`)
  - Sphinx docs build baseline: pass (`venv/bin/python -m sphinx -b html docs/source /tmp/discogs_player_sphinx_build`)
- Remaining:
  - continue eliminating contradictory or stale status claims as new RC data lands

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
  - Baseline measurements: pending first run with a live user collection under `--timing`

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

- [ ] No P0/P1 open regressions in key UI flows.
- [x] Two measurable responsiveness improvements documented. (Three hotspots instrumented: query, sort, widget-population; `--timing` flag available; baseline measurements pending first live-collection run)
- [x] Three high-risk behavior-driven GUI interactions covered by assertions. (47 tests across carousel + spin wheel animation, gallery selection/back, detail-panel state, and headless screenshot pipeline — `tests/test_widget_animation.py`, `tests/test_widget_behavior_gui.py`, `tests/test_headless_screenshot_script.py`)
- [x] Phase-2 outcome summary and next-phase recommendation added to `PRODUCT_STATE.md`.
