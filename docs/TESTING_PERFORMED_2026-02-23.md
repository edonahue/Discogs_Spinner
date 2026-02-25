# Testing Performed (2026-02-23)

This document records the local verification steps completed in this workspace before additional testing.

## Tooling Used

- `pytest 9.0.2`
- `mypy 1.19.1`
- `ruff 0.15.2`

## Commands Run And Outcomes

1. Lint (Ruff)

```bash
venv/bin/python -m ruff check .
```

Outcome:

- `All checks passed!`

2. Type-check (MyPy, full package)

```bash
venv/bin/python -m mypy src/discogs_player --show-error-codes --hide-error-context
```

Outcome:

- `Success: no issues found in 85 source files`

3. Unit/integration test suite (Pytest)

```bash
venv/bin/python -m pytest -q
```

Outcome:

- `312 passed, 3 skipped`

## Additional Iterative Validation During Fixes

Targeted MyPy checks were also run repeatedly during remediation on specific files using:

```bash
venv/bin/python -m mypy --follow-imports=skip <file...>
```

A focused GTK/UI file check was run with:

```bash
venv/bin/python -m mypy --follow-imports=skip --ignore-missing-imports src/discogs_player/ui/main_window.py
```

## Notes

- MyPy configuration in `pyproject.toml` now includes:
  - `ignore_missing_imports = true` for `gi`/`gi.*` modules, to handle environments where GTK stubs are unavailable.

## Post-Gallery Implementation Validation (2026-02-23)

After implementing the Browse/Wantlist Gallery mode, the same toolchain was run again.

1. Lint (Ruff)

```bash
venv/bin/ruff check .
```

Outcome:

- `All checks passed!`

2. Type-check (MyPy, full package)

```bash
venv/bin/python -m mypy src/discogs_player --show-error-codes --hide-error-context
```

Outcome:

- `Success: no issues found in 85 source files`

3. Unit/integration test suite (Pytest)

```bash
venv/bin/python -m pytest -q
```

Outcome:

- `314 passed, 3 skipped`

## Focused GTK Gallery Smoke Validation (2026-02-23)

These checks were run after implementing Gallery mode in Browse and Wantlist.

1. GUI startup smoke (headless GTK via `xvfb-run`)

```bash
./scripts/gui_smoke_test.sh 12
```

Outcome:

- JSON smoke report returned `ok: true` with `item_count: 12`, `cover_cached_count: 12`, and `titlebar_present: true`.

2. Focused Gallery interaction smoke (headless GTK, Browse + Wantlist)

Tooling:

- `xvfb-run` + `/usr/bin/python3` + GTK/libadwaita runtime

Checks executed in-process against `MainWindow`:

- switched Browse to `gallery`, verified no initial selection hides right panel (`sidebar_sensitive=false`, `sidebar_opacity=0.0`)
- selected a gallery album, verified right panel appears (`sidebar_sensitive=true`, `sidebar_opacity=1.0`)
- verified panel slide-left behavior via paned position change (`1185 -> 893`)
- clicked Gallery back button, verified selection clears and panel hides again (`893 -> 1185`)
- repeated same flow in Wantlist Gallery (`1185 -> 929 -> 1185`)

Outcome:

- All Gallery interaction assertions passed (`ok: true`).
- A GTK warning discovered during first pass (`set_min_content_width` vs prior max width) was fixed in `src/discogs_player/ui/main_window.py` by resetting max-content width before applying new min/max width, then interaction smoke was rerun cleanly.

## Comprehensive Recheck After Final Hardening (2026-02-23)

After adding a split-layout regression guard test, the full matrix was rerun.

1. Lint

```bash
venv/bin/ruff check .
```

Outcome:

- `All checks passed!`

2. Type-check

```bash
venv/bin/python -m mypy src/discogs_player --show-error-codes --hide-error-context
```

Outcome:

- `Success: no issues found in 85 source files`

3. Full automated test suite

```bash
venv/bin/python -m pytest -q
```

Outcome:

- `315 passed, 3 skipped`

4. GUI startup smoke

```bash
./scripts/gui_smoke_test.sh 12
```

Outcome:

- JSON output returned `ok: true` and `titlebar_present: true`.

5. Focused Gallery interaction smoke (headless GTK)

Outcome:

- Browse gallery panel behavior verified by position/visibility transitions:
  - hidden `position=1185`, `sidebar_sensitive=false`, `sidebar_opacity=0.0`
  - selected `position=893`, `sidebar_sensitive=true`, `sidebar_opacity=1.0`
  - back `position=1185`, `sidebar_sensitive=false`, `sidebar_opacity=0.0`
- Wantlist gallery panel behavior verified by position/visibility transitions:
  - hidden `position=1185`, `sidebar_sensitive=false`, `sidebar_opacity=0.0`
  - selected `position=929`, `sidebar_sensitive=true`, `sidebar_opacity=1.0`
  - back `position=1185`, `sidebar_sensitive=false`, `sidebar_opacity=0.0`

## Manual UX Exploratory Pass + Final Recheck (2026-02-23)

This pass focused on keyboard feel, mode/status messaging consistency, and gallery behavior under runtime interaction.

Enhancements implemented during pass:

- Gallery keyboard navigation now uses grid-aware stepping:
  - left/right move by one album
  - up/down move by current gallery column count
  - first keypress anchors to first visible album when no gallery selection is active
- Mode status messaging is now consistently updated when mode toggle buttons are clicked (not only via Enter key mode cycling).
- Gallery clear-selection status messages are now explicit:
  - `Browse gallery selection cleared.`
  - `Wantlist gallery selection cleared.`
- Initialization guard added in `_set_status` to avoid early-toggle status writes before `_status` exists.

Validation rerun after these changes:

1. Lint

```bash
venv/bin/ruff check .
```

Outcome:

- `All checks passed!`

2. Type-check

```bash
venv/bin/python -m mypy src/discogs_player --show-error-codes --hide-error-context
```

Outcome:

- `Success: no issues found in 85 source files`

3. Full automated suite

```bash
venv/bin/python -m pytest -q
```

Outcome:

- `316 passed, 3 skipped`

4. GUI startup smoke

```bash
./scripts/gui_smoke_test.sh 12
```

Outcome:

- JSON output returned `ok: true` and `titlebar_present: true`.

5. Focused gallery runtime smoke (Browse + Wantlist panel slide behavior)

Outcome:

- Passed (`ok: true`) with expected hidden/selected/back panel transitions in both sections.

6. Focused UX interaction smoke (mode status + gallery keyboard stepping)

Outcome:

- Passed (`ok: true`) with verified statuses:
  - Browse: `Browse mode: Gallery`, `Browse mode: Text Menu`, `Browse mode: Carousel`, `Browse gallery selection cleared.`
  - Wantlist: `Wantlist mode: Gallery`, `Wantlist mode: Text Menu`, `Wantlist mode: Carousel`, `Wantlist gallery selection cleared.`
- Verified keyboard sequence in Gallery:
  - Browse selected IDs: `3000 -> 3001 -> 3008` (down step used current columns `7`)
  - Wantlist selected IDs: `4000 -> 4001 -> 4008` (down step used current columns `7`)

## Reusable UX Smoke Script Added (2026-02-23)

To make this exploratory check repeatable, a one-command script was added:

```bash
./scripts/gallery_ux_smoke.sh 12
```

Script output (JSON) includes:

- `ok`
- `limit`
- `browse.columns_for_down_step`, `browse.statuses`, `browse.ids`
- `wantlist.columns_for_down_step`, `wantlist.statuses`, `wantlist.ids`

Validation after adding script + script test:

1. Lint

```bash
venv/bin/ruff check .
```

Outcome:

- `All checks passed!`

2. Type-check

```bash
venv/bin/python -m mypy src/discogs_player --show-error-codes --hide-error-context
```

Outcome:

- `Success: no issues found in 85 source files`

3. Full automated suite

```bash
venv/bin/python -m pytest -q
```

Outcome:

- `317 passed, 3 skipped`

## Performance/Responsiveness Pass Validation (2026-02-23)

This pass targeted UI runtime smoothness in gallery selection, gallery resize handling, and keyboard navigation lookup cost.

Validation after implementing optimizations:

1. Lint

```bash
venv/bin/ruff check .
```

Outcome:

- `All checks passed!`

2. Type-check

```bash
venv/bin/python -m mypy src/discogs_player --show-error-codes --hide-error-context
```

Outcome:

- `Success: no issues found in 85 source files`

3. Full automated suite

```bash
venv/bin/python -m pytest -q
```

Outcome:

- `319 passed, 3 skipped`

4. GUI startup smoke

```bash
./scripts/gui_smoke_test.sh 12
```

Outcome:

- JSON returned `ok: true` with `item_count: 12`, `cover_cached_count: 12`, and `titlebar_present: true`.

5. Gallery UX smoke

```bash
./scripts/gallery_ux_smoke.sh 12
```

Outcome:

- JSON returned `ok: true`, with expected mode status transitions and gallery keyboard stepping IDs for both Browse and Wantlist.

## Full Accuracy + Performance Audit (2026-02-23, latest)

This pass was executed after the latest feature additions and included targeted runtime improvements discovered during audit.

### Runtime Enhancements Applied During Audit

- `CoverGrid` now debounces resize/layout updates (`_RESIZE_DEBOUNCE_MS`) to reduce repeated relayout work during continuous window resizing.
- `MainWindow` now uses bounded in-memory LRU caches for release/wantlist tracklist detail payloads to avoid repeated DB reads while navigating between already-viewed items.
- `LazyImageLoader` correctness/perf hardening:
  - fixed in-flight cancellation to cancel the actual stored future
  - clamped simulated priority sleep delay to non-negative values
  - corrected nearby preload window bounds (`radius` handling)

### Tooling Used

- `pytest 9.0.2`
- `ruff 0.15.2`
- `mypy 1.19.1`
- `xvfb-run` headless GTK smoke execution

### Commands Run And Outcomes

1. Focused regression checks (design/perf/responsive guards)

```bash
venv/bin/pytest -q tests/test_gui_design_consistency.py tests/test_performance_optimizations.py tests/test_window_resizing_improvements.py
```

Outcome:

- `39 passed, 3 skipped`

2. Lint

```bash
venv/bin/ruff check .
```

Outcome:

- `All checks passed!`

3. Type-check

```bash
venv/bin/mypy src
```

Outcome:

- `Success: no issues found in 85 source files`

4. Full automated suite

```bash
venv/bin/pytest -q
```

Outcome:

- `323 passed, 5 skipped in 36.27s`

5. GUI startup smoke

```bash
./scripts/gui_smoke_test.sh 12
```

Outcome:

- JSON returned `ok: true` with `item_count: 12`, `cover_cached_count: 12`, and `titlebar_present: true`.

6. Gallery interaction smoke

```bash
./scripts/gallery_ux_smoke.sh 12
```

Outcome:

- JSON returned `ok: true`, including expected Browse/Wantlist status transitions and grid-step keyboard ID movements.

7. Full-suite duration profile (hotspot audit)

```bash
venv/bin/pytest -q --durations=20
```

Outcome:

- `323 passed, 5 skipped in 36.05s`
- Top hotspots remained integration/script simulations (e.g., Spotify slow-map smoke failure-path test at ~1.03s), not UI rendering paths.

8. Performance module skip visibility (environment/runtime constraints)

```bash
venv/bin/pytest -q tests/test_performance_optimizations.py -rs
```

Outcome:

- `1 passed, 3 skipped`
- Skips are explicit and expected where GTK runtime dependencies are unavailable in the test interpreter:
  - `Performance module requires GTK dependencies`

## Gallery Runtime Benchmark (GTK headless, 2026-02-23)

Executed a dedicated Browse/Wantlist gallery latency benchmark twice under `xvfb-run` with live GTK event-loop pumping and 240-item datasets in each section.

Benchmark dimensions per run:

- release load timing (Browse and Wantlist)
- gallery selection timing (first pass/cold vs repeated pass/warm)
- gallery next-item navigation step timing
- gallery resize burst timing + debounced layout-call count

Environment:

- `xvfb-run -a /usr/bin/python3`
- `PYTHONPATH=src`
- `GSK_RENDERER=cairo`
- `LIBGL_ALWAYS_SOFTWARE=1`
- writable `XDG_RUNTIME_DIR` in `/tmp`

Measured ranges across two runs:

- Load:
  - Browse: `237.6ms` to `239.2ms`
  - Wantlist: `239.1ms` to `241.7ms`
- Select cold (first-hit, 60 samples):
  - Browse avg: `0.568ms` to `0.570ms`; p95: `0.602ms` to `0.613ms`
  - Wantlist avg: `0.555ms` to `0.556ms`; p95: `0.605ms` to `0.615ms`
- Select warm (repeat-hit, 60 samples):
  - Browse avg: `0.215ms` to `0.219ms`; p95: `0.224ms` to `0.231ms`
  - Wantlist avg: `0.197ms` to `0.200ms`; p95: `0.207ms` to `0.210ms`
- Navigation step (120 samples, gallery mode):
  - Browse avg: `11.387ms` to `11.824ms`; p95: `33.032ms` to `35.379ms`
  - Wantlist avg: `13.127ms` to `13.491ms`; p95: `58.424ms` to `60.498ms`
- Resize burst (180 rapid hints each):
  - enqueue time: `0.072ms` to `0.093ms`
  - debounced layout calls: Browse `1` to `2`; Wantlist `1`
  - settled total around `320ms` reflects intentional post-burst settle window, not direct layout work time.

Observations:

- Browse and Wantlist selection latency is sub-millisecond and stable.
- Warm selection is consistently faster than cold selection, matching expected cache behavior.
- Debounced gallery resize is effective (single-digit layout reflows across 180 rapid resize hints).
- Navigation remains smooth on average, with occasional higher-tail samples under headless timing noise and cross-component update work.

## Wantlist Navigation Tail-Latency Reduction (2026-02-23)

Goal:

- reduce Wantlist gallery navigation tail latency (p95) to be closer to Browse and improve perceived smoothness.

Concrete patch:

- `src/discogs_player/ui/main_window.py`
  - navigation stepping now focuses selected IDs immediately (instead of queuing each step through `GLib.idle_add`) in:
    - `_navigate_selection`
    - `_navigate_wantlist_selection`
  - split-layout reflow on selection change now runs only when gallery detail visibility actually changes (no-selection -> selection or selection -> no-selection), via `_should_reflow_gallery_split`.

Validation after patch:

1. Targeted checks

```bash
venv/bin/ruff check src/discogs_player/ui/main_window.py tests/test_gui_design_consistency.py
venv/bin/mypy src/discogs_player/ui/main_window.py
venv/bin/pytest -q tests/test_gui_design_consistency.py tests/test_gallery_ux_smoke_script.py tests/test_window_resizing_improvements.py
```

Outcome:

- lint/type clean
- `38 passed, 1 skipped`

2. Full verification

```bash
venv/bin/pytest -q
./scripts/gui_smoke_test.sh 12
./scripts/gallery_ux_smoke.sh 12
```

Outcome:

- `323 passed, 5 skipped`
- GUI smoke and gallery UX smoke both returned `ok: true`.

Before/after benchmark report (same GTK headless harness, 2 runs each):

- Before (pre-patch), Wantlist nav step:
  - avg: `13.127ms` to `13.491ms`
  - p95: `58.424ms` to `60.498ms`
- After (post-patch), Wantlist nav step:
  - avg: `6.272ms` to `6.708ms`
  - p95: `9.032ms` to `9.891ms`

Measured improvement:

- Wantlist nav avg reduced by roughly `~49%` to `~53%`.
- Wantlist nav p95 reduced by roughly `~83%` to `~85%`.

Cross-check:

- Browse nav step also improved in the same run shape:
  - avg moved from `11.387ms` to `11.824ms` -> `7.764ms` to `7.939ms`
  - p95 moved from `33.032ms` to `35.379ms` -> `17.124ms` to `17.404ms`
