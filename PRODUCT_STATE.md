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

### Validation Baseline (As Of 2026-02-26)

Most recent recorded validation:

- `prepublish_hygiene_check.sh`: passing
- `ruff`: passing
- `mypy`: passing (`92` source files checked)
- `pytest -q`: `362 passed, 4 skipped`
- `npm --prefix webapp run build`: passing

Reference: `docs/TESTING_PERFORMED_2026-02-26.md`

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

- Phase 1 (Documentation Convergence, 2026-02-23 to 2026-03-01): In progress; canonical-state ownership, README alignment, and historical-doc positioning are largely done. Remaining work includes Sphinx toctree/file alignment.
- Phase 2 (Stabilization And Responsiveness, 2026-03-01 to 2026-03-31): Pre-kickoff groundwork is in place (`STABILIZATION_BACKLOG_2026Q1.md`, execution tracker); full execution is next.
- Phase 3 (UX Simplification And Flow Hardening, 2026-04-01 to 2026-04-30): Not started.
- Phase 4 (Next Feature Block, 2026-05-01 to 2026-06-30): Not started.

## Current Gaps And Risks

1. Documentation drift

- Some historical status files report outdated test counts/completeness snapshots.
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

1. Close remaining manual checklist items for `v0.2.0-rc4` (clean-machine pilot validations on Windows/Debian/macOS) and re-evaluate rollout go/no-go.
2. Execute 72-hour post-release follow-up loop from issue `#1` and capture friction outcomes.
3. Continue Phase-2 stabilization execution (`STABILIZATION_BACKLOG_2026Q1.md`, `docs/STABILIZATION_EXECUTION_2026Q1.md`).
