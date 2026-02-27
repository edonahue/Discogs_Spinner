# Phase 3: UX Simplification And Flow Hardening — Scope

Date: 2026-02-26 (drafted at Phase 2 close)
Window: 2026-04-01 to 2026-04-30
Status: Ready to start
Reference: `PRODUCT_STATE.md` → Phase 3 section

---

## Goal

Reduce cognitive load across Browse and Wantlist flows while preserving
advanced capability. Make the default path obvious for new users; keep
power controls accessible but not intrusive.

---

## Decisions To Make Before Starting

These must be answered (with owner + date) before implementation begins.

### D1: Default browse/wantlist mode

On first launch (no saved preference), which mode should Browse and Wantlist
open in?

| Option | Trade-off |
|---|---|
| Gallery (cover grid) | Most visual; highest widget-population cost |
| Carousel | Familiar CD-spinner metaphor; good for small collections |
| Text menu | Fastest to load; works over SSH |

**Current default**: Carousel — hardcoded in `MainWindow.__init__` (lines 1132–1133
for wantlist, 1350–1351 for browse). Mode is not persisted across restarts, so
the app always opens in Carousel.
**Decision**: **Carousel (2026-02-27, Erich).** No code change required; existing
startup behavior is correct. Mode persistence across restarts is explicitly out of
scope for Phase 3.

---

### D2: "Switched to X view" tab-switch messages

Every time the user clicks a mode toggle (Carousel / Text Menu / Gallery),
a status message fires: `"Switched to carousel view"` etc.

Options:

| Option | Trade-off |
|---|---|
| Keep as-is | Provides feedback, but fires on every click — noisy for power users |
| Suppress entirely | Cleaner for experienced users; no feedback for new users |
| Replace with transient toast | GTK4 `Adw.Toast` — visible for ~2s then auto-dismissed |
| Rate-limit (suppress repeats) | Only show if mode actually changed from last shown message |

**Recommendation**: Replace with `Adw.Toast` (transient, non-blocking, auto-dismissed).
**Decision**: **Keep as-is (2026-02-27, Erich).** The `_set_status()` messages on
mode toggle are retained. No code change.

---

### D3: First-run / empty-state experience

When a new user launches the GUI with no local data synced, the current UX is:

> "No releases loaded. Run "dplayer sync" to import your Discogs collection."

Questions:
- Should the GUI offer a "Sync now" button inline in the empty state?
- Should a first-launch dialog walk through token setup + first sync?

**Recommendation**: Add a "Sync now" button to the Browse empty-state label
(wires to the existing sync handler). Defer full FTUX dialog to Phase 4
(out of scope for simplification).
**Decision**: **Complete (2026-02-27).** Implemented in `feat(gui): first-run onboarding`
and `feat(onboarding)` commits. Browse and Wantlist both have inline Sync buttons,
three-tier empty-state messages, and per-page progress feedback.

---

### D4: Responsiveness gate

Phase 2 left one open measurement: widget-population latency under
`dplayer-gui --timing` against a real collection.

**Rule**: If `widgets` latency in a browse-load exceeds 200ms with a typical
collection (200–2000 releases), a virtualization pass (`VirtualizedGrid`
from `ui/performance.py`) must be completed *before* UX simplification work
begins — otherwise any UX work is built on a sluggish foundation.

**Gate**: Record timing run first. If widgets < 200ms, proceed to D1–D3
implementation. If ≥ 200ms, add a pre-Phase 3 spike for virtualization.

---

## Implementation Scope (Once Decisions Are Made)

Ordered by dependency:

1. **Timing gate** — run `dplayer-gui --timing`; record numbers; decide on
   virtualization spike vs. proceed.
2. **Default mode** (D1) — add a `default_browse_mode` setting to
   `core/settings.py`; wire into `MainWindow` initial tab selection.
3. **Tab-switch messages** (D2) — replace `_set_status()` calls in
   `_set_browse_mode()` and `_set_wantlist_mode()` with `Adw.Toast`.
4. **Empty-state "Sync now" button** (D3) — add a `Gtk.Button` to the
   empty-state overlay in Browse and Wantlist panels.
5. **Regression tests** — behavior assertions for default mode on fresh start,
   toast fires on mode switch, sync button triggers handler.

---

## Out Of Scope For Phase 3

- Full FTUX onboarding dialog (Phase 4)
- New data features (Value Movers, Price Refresh Prioritizer)
- Mobile companion / multi-provider

---

## Success Criteria

- [x] Default mode decision made and implemented; no mode-unknown state on first launch. *(D1: Carousel — existing behavior is correct; no code change required. 2026-02-27)*
- [x] Tab-switch status message treatment decided. *(D2: Keep as-is — `_set_status()` calls on mode toggle retained. No code change. 2026-02-27)*
- [x] Empty-state panels include an actionable affordance (button or inline instruction). *(D3: Browse + Wantlist Sync buttons, three-tier messages, per-page progress — shipped in feat(onboarding) commits. 2026-02-27)*
- [x] Full validation matrix green. *(`454 passed, 4 skipped`; ruff clean; mypy 92 files; npm build — 2026-02-27)*
- [x] No new P0/P1 regressions introduced. *(454 tests passing; no regressions detected.)*
- [ ] D4 timing gate: record `dplayer-gui --timing` latencies against live collection in `docs/STABILIZATION_EXECUTION_2026Q1.md`. *(Needs desktop session — pending.)*
