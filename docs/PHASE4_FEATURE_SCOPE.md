# Phase 4: Next Feature Block (Discogs-First ROI) — Scope

Date: 2026-02-27 (drafted at Phase 3 decision closure)
Window: 2026-05-01 to 2026-06-30
Status: Ready to scope; not yet started
Reference: `PRODUCT_STATE.md` → Phase 4 section, `DISCOGS_STRETCH_GOALS.md`

---

## Goal

Ship one high-ROI, Discogs-native feature track end-to-end — use case, CLI surface, GUI
exposure, tests, and docs — before opening the next. Keep existing infrastructure
unchanged; build on top of current value snapshot/refresh layer.

---

## Existing Infrastructure (Do Not Duplicate)

| Module | What it provides |
|---|---|
| `use_cases/value_dashboard.py` | Assembles market-value dashboard data (examples, status, trends, duplicates) |
| `use_cases/value_trend.py` | Compares current prices to a previous snapshot |
| `use_cases/value_snapshot.py` | Takes point-in-time snapshots of collection market values |
| `use_cases/value_refresh.py` | Refreshes market prices from Discogs API |
| `use_cases/value_missing.py` | Identifies releases with no market-price data |
| `use_cases/duplicate_variant_detector.py` | Detects duplicate releases and format variants |
| `use_cases/collection_analytics.py` | Genre/decade/label analytics over local collection |
| `data/repo.py` | All DB queries; add new queries here, not inline in use cases |

---

## Candidate Feature Tracks (Ordered By Priority)

### Track A: Value Movers Panel

**What it is**: Shows what changed most in market value between the last two snapshots —
top gainers and decliners, with delta amounts and percentages.

**Why now**: Snapshot infrastructure (`value_snapshot.py`, `value_trend.py`) is already in
place. This is a read-only aggregation layer with no new API calls.

**Existing hook**: `value_trend.py` already computes per-release deltas between snapshots.
The panel needs a `top_movers(n)` aggregation and a GUI list widget.

---

### Track B: Price Refresh Prioritizer

**What it is**: A queue that orders refresh budget by priority:
`unpriced > stale > high-value` — so refresh API calls go where they matter most first.

**Why now**: `value_missing.py` and `value_refresh.py` exist but refresh is currently
unordered. A prioritizer reduces wasted API budget and improves data freshness for the
releases that matter.

---

### Track C: Collection Health Score

**What it is**: A single composite score (0–100) summarising collection data quality,
with breakdown by issue bucket: missing price, missing year, missing genre/style,
missing cover art, no tracklist.

**Why now**: Data-quality signals are scattered (value_missing, existing analytics).
A single score makes cleanup measurable and motivating.

---

## Decisions To Make Before Starting

### D1: Which track to ship first

**Selection rule**: Choose one primary feature track and complete it end-to-end before
opening the next. Avoid parallel partial implementations.

| Option | Rationale |
|---|---|
| Track A — Value Movers | Smallest delta from existing infrastructure; high visual impact |
| Track B — Price Refresh Prioritizer | Directly reduces API waste; operational benefit |
| Track C — Collection Health Score | Highest user-facing clarity; depends on no existing infra |

**Decision**: *(owner + date — fill before implementation begins)*

---

### D2: CLI-first or GUI-first delivery

For whichever track is selected: should the first working implementation target the CLI
(`dplayer value movers`, `dplayer value queue`, `dplayer health`) or the GUI panel?

| Option | Trade-off |
|---|---|
| CLI first | Faster feedback loop; testable without GTK; consistent with project principles |
| GUI first | Higher visual impact; but harder to test headlessly |
| Simultaneous | Risk of split focus; avoid unless the feature is trivially small |

**Recommendation**: CLI first, then wire into GUI panel — consistent with project
architecture (no API calls in UI, shared use-cases).

**Decision**: *(owner + date)*

---

### D3: Snapshot dependency handling

Value Movers (Track A) requires at least two snapshots to show a delta. What should the
panel show when only one snapshot exists?

| Option | Trade-off |
|---|---|
| Empty state with "Take a snapshot first" prompt | Clear; honest |
| Show absolute values only (no delta) | Useful immediately; delta available after second snapshot |
| Block feature until two snapshots exist | Too restrictive |

**Recommendation**: Show absolute values on first snapshot; add delta column after a second
snapshot is available.

**Decision**: *(owner + date)*

---

## Implementation Scope (Track A — Value Movers, Assumed First)

Ordered by dependency:

1. **`use_cases/value_movers.py`** — `run_value_movers(limit=10)` function.
   - Reads the two most recent snapshots from the DB.
   - Computes per-release delta (absolute + percent).
   - Returns sorted lists: top gainers, top decliners, no-movement.
   - Returns graceful empty state when < 2 snapshots exist.

2. **CLI command** — `dplayer value movers [--limit N] [--json]` via existing
   `cli/commands.py` value group.

3. **GUI panel** — Add a "Movers" sub-view to the existing Market Value dashboard tab.
   Wire to `value_movers.py` via the existing async action pattern.

4. **DB query** — Add `get_two_most_recent_snapshots()` to `data/repo.py` if not already
   present.

5. **Tests** — Unit tests for `run_value_movers()` with fixture snapshots; CLI invocation
   test; GUI source-level assertion that the panel wires the use case.

---

## Out Of Scope For Phase 4

- Full FTUX onboarding dialog (deferred)
- Mobile companion / multi-provider (YouTube Music — Phase 5+)
- Qt6 / cross-platform GUI migration (longer horizon)
- Spotify feature expansion (separate track)

---

## Success Criteria

- [ ] D1 feature track selected with owner + date recorded in this doc.
- [ ] D2 delivery order decided (CLI-first recommended).
- [ ] D3 snapshot edge case handled per decision.
- [ ] Selected feature: use case, CLI command, and GUI exposure all complete.
- [ ] At least 5 new tests covering the new use case (unit + integration).
- [ ] Full validation matrix green (`ruff`, `mypy`, `pytest`, web build).
- [ ] No regressions in existing value dashboard or wantlist flows.
- [ ] Feature documented in `dplayer --help` and at least one quickstart doc update.
