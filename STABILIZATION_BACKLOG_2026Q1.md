# Stabilization Backlog (2026 Q1)

Date: 2026-02-23 (UTC)
Scope window: 2026-03-01 to 2026-03-31
Source roadmap: `PRODUCT_STATE.md` (Phase 2)
Execution tracker: `docs/STABILIZATION_EXECUTION_2026Q1.md`

## Scope Guardrails

In scope:

- bug fixes,
- runtime/performance improvements,
- usability hardening,
- high-risk test coverage expansion.

Out of scope:

- net-new feature tracks (Value Movers, Prioritizer, etc.),
- broad UI redesign unrelated to known usability/performance risks,
- cross-platform migration work.

## Success Criteria

1. Full validation matrix stays green:

- `venv/bin/ruff check .`
- `venv/bin/python -m mypy src/discogs_player --show-error-codes --hide-error-context`
- `venv/bin/python -m pytest -q`
- `./scripts/gui_smoke_test.sh 12`
- `./scripts/gallery_ux_smoke.sh 12`

2. No P0/P1 open regressions in Browse/Wantlist/Market Value interaction flows.

3. Documented responsiveness improvements in at least two measurable hotspots.

4. Behavior-driven GUI tests added for at least three high-risk interactions.

## Priority Workstreams

### P0: Documentation/Operational Correctness

1. Converge user-visible docs to canonical state model.
2. Remove conflicting stale status claims in top-level docs.
3. Keep testing evidence file current after each stabilization change set.

Owner: Docs + Engineering
Exit condition: no contradictory "current status" claims remain.

### P1: Runtime Responsiveness

1. Reduce avoidable O(n) work in UI interaction paths.
2. Add lightweight timing hooks for key interaction latency (debug path only).
3. Validate no regressions in keyboard navigation and split-pane updates.

Owner: UI Engineering
Exit condition: measured improvement and no interaction regressions.

### P1: Usability Hardening

1. Standardize status messages for mode changes, selections, and action outcomes.
2. Tighten empty/error/loading states in Browse, Wantlist, and Market Value tabs.
3. Ensure default usage path remains obvious without hiding advanced controls.

Owner: UX + UI Engineering
Exit condition: no dead-end states in smoke + manual walkthrough.

### P1: GUI Behavior Test Expansion

1. Add behavior assertions for gallery selection/back and right-panel visibility.
2. Add interaction tests for mode toggles and keyboard navigation focus behavior.
3. Add split-layout transition tests across Browse/Wantlist tab switches.

Owner: QA + UI Engineering
Exit condition: high-risk interaction tests run in CI with stable pass rate.

### P2: Stability Debt Cleanup

1. Triage root-level debug/scratch scripts and classify keep/remove/archive.
2. Reduce doc/test duplication where it increases maintenance overhead.
3. Record known residual risks for post-stabilization planning.

Owner: Engineering
Exit condition: reduced maintenance ambiguity and explicit deferred-risk list.

## Weekly Cadence

Week 1 (starting 2026-03-01):

- finalize doc convergence and baseline measurements.

Week 2:

- ship first responsiveness + usability patch set.

Week 3:

- ship GUI behavior test expansion and regression hardening.

Week 4:

- close residual P1s, publish stabilization summary, confirm readiness for next feature block.

## Definition Of Done (Phase 2)

Phase 2 is complete only when:

1. Success criteria are met,
2. open P0/P1 items are resolved or explicitly deferred with rationale,
3. `PRODUCT_STATE.md` is updated with stabilization outcomes and next-phase readiness.
