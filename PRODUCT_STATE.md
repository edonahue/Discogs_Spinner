# Product State: discogs_player

Date: 2026-02-23 (UTC)
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

## Source-Of-Truth Order

When docs disagree, use this precedence:

1. `PRODUCT_STATE.md` (this file)
2. `README.md` (user-facing usage + setup)
3. `docs/TESTING_PERFORMED_2026-02-23.md` (latest validation evidence)
4. ADRs in `docs/adr/`
5. Older summaries (`PROJECT_SNAPSHOT.md`, `PROJECT_ASSESSMENT.md`, `DOCUMENTATION_SUMMARY.md`)

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

### Validation Baseline (As Of 2026-02-23)

Most recent recorded validation:

- `ruff`: passing
- `mypy`: passing
- `pytest -q`: `319 passed, 3 skipped`
- GUI smoke: passing
- Gallery UX smoke: passing

Reference: `docs/TESTING_PERFORMED_2026-02-23.md`

## Current Gaps And Risks

1. Documentation drift

- Some status files report outdated test counts/completeness snapshots.
- Sphinx toctree references pages that are not present under `docs/source/`.

2. Product focus drift

- Original "CLI-first, thin GUI" intent is still valid architecturally, but feature growth has increased UI complexity.
- Default UX paths should stay simple while retaining advanced controls.

3. Test strategy imbalance

- Strong automated coverage exists, but many GUI checks are static marker tests and smoke checks.
- More behavior/assertion-based GUI tests are needed for complex interaction flows.

4. Release readiness housekeeping

- Public-release checklist items (license/history/data hygiene, portability messaging) need explicit closure tracking.

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
Window: 2026-03-01 to 2026-03-31
Goal: Improve perceived performance and reduce UI regressions.

Deliverables:

- Execute `STABILIZATION_BACKLOG_2026Q1.md` under strict stabilization scope
- Continue targeted UI runtime optimizations (selection, resize, navigation)
- Add behavior-driven GUI tests for gallery/carousel/wantlist/detail interactions
- Add lightweight performance instrumentation for key interaction latency

Success criteria:

- No critical regressions across full test + smoke matrix
- Improved interaction responsiveness under typical datasets

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

These are the immediate next actions following this document:

1. Documentation sync pass (README + status docs + Sphinx index)
2. Stabilization backlog execution (`STABILIZATION_BACKLOG_2026Q1.md`)
3. GUI behavior-test expansion for high-risk interactions
