# v1.0 Release Flow

The single entry point for cutting `v1.0.0`. The v1.0 docs are otherwise spread
across several files; this is the ordered path that chains them together. Each
step links to the authoritative doc for that step — this index stays short on
purpose and does not duplicate their content.

> Status: aspirational target. Keep shipping `0.x` releases until every gate
> below is green. Live gate status lives in **[V1_READINESS_TRACKER.md](V1_READINESS_TRACKER.md)**.

## The path

1. **Know what 1.0 means.** Read the promise, required gates, and explicit
   non-goals in **[RELEASE_TARGET_v1.0.md](RELEASE_TARGET_v1.0.md)**.

2. **Check gate status.** **[V1_READINESS_TRACKER.md](V1_READINESS_TRACKER.md)**
   is the live checklist — it lists every gate, whether it's done/open, and where
   the evidence lives. Work the open gates below; don't tag until all are closed.

3. **Stand up signing trust.** Follow **[SIGNING.md](SIGNING.md)** to add the
   GitHub signing secrets. `installer_build.yml` is already wired to consume them
   (it builds unsigned when they're absent, signed when present), so this gate is
   "set the secrets + verify a signed artifact" — no workflow code changes.

4. **Capture a timing baseline.** Run `dplayer-gui --timing` against a real
   collection once and record browse/wantlist latencies in
   **[STABILIZATION_EXECUTION_2026Q1.md](STABILIZATION_EXECUTION_2026Q1.md)**
   (Baseline Measurements table).

5. **Run clean-machine FTUX on each OS.** Use the per-OS gate checklist in
   **[RELEASE_CHECKLIST_WINDOWS_DEBIAN_MACOS.md](RELEASE_CHECKLIST_WINDOWS_DEBIAN_MACOS.md)**,
   filling in the matching validation record:
   - Windows → [validation/windows_tauri_ftux.md](validation/windows_tauri_ftux.md)
   - macOS → [validation/macos_installer_ftux.md](validation/macos_installer_ftux.md)
   - Debian → [validation/debian_installer_ftux.md](validation/debian_installer_ftux.md)

6. **Run the friend/beta trial.** Hand the cohort
   **[friend_trial.md](friend_trial.md)** (or the short
   **[friend_trial_checklist.md](friend_trial_checklist.md)**); log friction in the
   tracker's friend-trial table and close or explicitly accept P0/P1 items.

7. **Cut the release.** Once the tracker is all-green, follow
   **[PUBLIC_RELEASE_RUNBOOK.md](PUBLIC_RELEASE_RUNBOOK.md)** to tag and publish via
   `installer_build.yml`. (The older tarball-based `RC_RELEASE_RUNBOOK.md` is
   deprecated — see its banner.)

8. **Push to stores.** After the GitHub Release publishes, work the channels in
   **[STORE_SUBMISSIONS.md](STORE_SUBMISSIONS.md)** (its Submission Readiness
   Snapshot lists each channel's next blocker).

## At a glance

| # | Step | Gate it closes | Authoritative doc |
|---|------|----------------|-------------------|
| 1 | Define 1.0 | product contract | RELEASE_TARGET_v1.0.md |
| 2 | Track gates | — (the tracker) | V1_READINESS_TRACKER.md |
| 3 | Signing | Windows + macOS signing | SIGNING.md |
| 4 | Timing | live timing baseline | STABILIZATION_EXECUTION_2026Q1.md |
| 5 | FTUX ×3 | clean-machine FTUX | RELEASE_CHECKLIST_WINDOWS_DEBIAN_MACOS.md + validation/*_ftux.md |
| 6 | Friend trial | beta cohort reviewed | friend_trial.md |
| 7 | Cut release | RC automation + manual gates | PUBLIC_RELEASE_RUNBOOK.md |
| 8 | Stores | (post-1.0 distribution) | STORE_SUBMISSIONS.md |

Already closed (not gates you need to re-run): CI quality gates — lint, type
check, full test suite, and webapp lint/type/tests all run on every push (see the
tracker).
