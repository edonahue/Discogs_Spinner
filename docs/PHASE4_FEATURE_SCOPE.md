# Phase 4: Next Feature Block (Discogs-First ROI) — Scope

Date: 2026-02-27 (drafted at Phase 3 decision closure; updated 2026-02-27 after schema audit)
Window: 2026-05-01 to 2026-06-30
Status: Ready to scope; Track A and Track B started (CLI-first)
Reference: `PRODUCT_STATE.md` → Phase 4 section, `DISCOGS_STRETCH_GOALS.md`

---

## Goal

Ship high-ROI, Discogs-native features end-to-end — use case, CLI surface, tests, and
docs — one track at a time. Keep existing infrastructure unchanged; build on top of
current value snapshot/refresh layer.

---

## Existing Infrastructure (Do Not Duplicate)

| Module | What it provides |
|---|---|
| `use_cases/value_dashboard.py` | Assembles market-value dashboard data (examples, status, trends, duplicates) |
| `use_cases/value_trend.py` | Compares collection-level totals between snapshots |
| `use_cases/value_snapshot.py` | Takes point-in-time collection-level snapshots |
| `use_cases/value_refresh.py` | Refreshes market prices from Discogs API |
| `use_cases/value_missing.py` | Identifies releases with no market-price data |
| `use_cases/duplicate_variant_detector.py` | Detects duplicate releases and format variants |
| `use_cases/collection_analytics.py` | Genre/decade/label analytics over local collection |
| `data/repo.py` | All DB queries; add new queries here, not inline in use cases |

### Schema Constraint Note (2026-02-27)

`market_prices` stores **only the current price** per release (one row per release,
updated in place). `market_value_snapshots` stores **collection-level totals only** —
no per-release breakdown. Per-release price history does not exist in the current schema.

**Impact on Track C (Value Movers)**: computing per-release gainers/decliners between
snapshots requires a new `market_price_history` table and a schema migration. This is
explicitly gated on a schema design decision (see Track C below).

---

## Feature Tracks (Revised Priority Order)

### Track A: Price Refresh Prioritizer *(started)*

**What it is**: A queue that orders refresh budget by priority:
`unpriced > stale-high-value > stale-low-value` — so Discogs API refresh calls go
where they matter most first.

**Status**: CLI use case and command implemented (`use_cases/value_refresh_queue.py`,
`dplayer value queue`). Tests written.

**Existing hooks used**:
- `data/repo.query_releases_needing_market_refresh()` — returns candidates with
  `market_need_reason` (`missing` / `unpriced` / `stale`)
- `data/repo.query_market_value_examples()` — for high-value context

**No schema changes required.**

---

### Track B: Collection Health Score *(started)*

**What it is**: A single composite score (0–100) summarising collection data quality,
with per-bucket breakdown: missing price, missing year, missing genres, missing cover
art, unmatched (Spotify).

**Status**: CLI use case and command implemented (`use_cases/collection_health.py`,
`dplayer health`). Tests written.

**Existing hooks used**: `releases` table + `market_prices` join + `spotify_mappings`
join — all existing.

**No schema changes required.**

---

### Track C: Value Movers Panel *(blocked — schema migration required)*

**What it is**: Shows what changed most in market value between the last two snapshots —
top gainers and decliners, with delta amounts and percentages.

**Blocker**: No per-release price history exists. `market_prices` stores only the
current price (updated in place). Implementing this requires:

1. A new DB migration adding a `market_price_history` table
   (`discogs_release_id`, `snapshot_id`, `median`, `lowest`, `highest`, `captured_at`).
2. Modifying `run_market_value_snapshot()` to also insert per-release rows into
   `market_price_history` at snapshot time.
3. A new `query_value_movers(conn, *, snapshot_a_id, snapshot_b_id, limit)` in
   `data/repo.py`.
4. `use_cases/value_movers.py` — fetches the two most recent snapshot IDs, queries
   per-release deltas, returns sorted gainers/decliners.

**Gate**: Schema migration must be designed and reviewed before implementation begins.
Migration must be backward-compatible (existing `market_value_snapshots` rows remain
valid; new per-release history is empty until the next snapshot is taken).

---

## Decisions To Make Before Starting GUI Phase

### D1: Track order *(resolved 2026-02-27)*

**Decision**: Track A (Price Refresh Prioritizer) first, Track B (Collection Health
Score) second, Track C (Value Movers) third pending schema design.

### D2: CLI-first or GUI-first *(resolved 2026-02-27)*

**Decision**: CLI first for all tracks. GUI wiring follows after CLI is tested and
stable. Consistent with project architecture (no API calls in UI, shared use-cases).

### D3: Value Movers snapshot edge case *(deferred — Track C gated)*

When only one snapshot exists, show absolute current values with no delta column.
Delta column appears after the second snapshot is taken.

**Decision**: Agreed in principle; implement when Track C unblocks.

### D4: Schema migration for Value Movers *(open — needs owner + date)*

Requires deciding:
- Table name and column set for `market_price_history`
- Whether to backfill historical data (not possible without re-running old refreshes)
- Whether per-release snapshot capture runs synchronously or as a background job

---

## Implementation Scope Completed (2026-02-27)

### Track A: Price Refresh Prioritizer

- `src/discogs_player/use_cases/value_refresh_queue.py` — `run_value_refresh_queue(limit)`
- `dplayer value queue [--limit N] [--json]` CLI command in `cli/commands.py`
- `tests/test_value_refresh_queue.py`

### Track B: Collection Health Score

- `src/discogs_player/use_cases/collection_health.py` — `run_collection_health()`
- `dplayer health [--json]` CLI command in `cli/commands.py`
- `tests/test_collection_health.py`

---

## Out Of Scope For Phase 4

- Full FTUX onboarding dialog (deferred)
- Mobile companion / multi-provider (YouTube Music — Phase 5+)
- Qt6 / cross-platform GUI migration (longer horizon)
- Spotify feature expansion (separate track)

---

## Success Criteria

- [x] D1 track order decided. *(Track A → B → C; 2026-02-27)*
- [x] D2 delivery order decided. *(CLI-first; 2026-02-27)*
- [x] Track A use case, CLI command, and tests complete.
- [x] Track B use case, CLI command, and tests complete.
- [ ] Track A and Track B GUI panel wiring (post-CLI phase).
- [ ] Track C schema migration designed and reviewed (D4 decision).
- [ ] Track C implementation end-to-end.
- [ ] Full validation matrix green after each track (`ruff`, `mypy`, `pytest`, web build).
- [ ] No regressions in existing value dashboard or wantlist flows.
- [ ] Features documented in `dplayer --help`.
