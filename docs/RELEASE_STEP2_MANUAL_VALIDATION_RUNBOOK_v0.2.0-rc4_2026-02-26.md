# Step 2 Manual Validation Runbook (`v0.2.0-rc4`)

Date opened: 2026-02-26 (UTC)  
Owner: Engineering  
Status: In Progress

Source checklist: `docs/RELEASE_CHECKLIST_WINDOWS_DEBIAN_MACOS.md`  
Live status ledger: `docs/RELEASE_CHECKLIST_STATUS_v0.2.0-rc4_2026-02-26.md`

## Purpose

Close all remaining manual validation gates required to move from pilot-only
`NO-GO` toward a widen-audience `GO/NO-GO` re-evaluation.

## Completion Rule

This runbook is complete only when:

1. Every task in the tracker below is marked `PASS`,
2. each task has concrete evidence links populated,
3. any failures are linked to tracked issues with mitigation decisions recorded.

## Evidence Standard (Per Task)

Required evidence fields:

- environment details (OS version, install path, tester identity/role),
- execution proof (commands run and/or explicit user-path walkthrough),
- result artifact link (log, screenshot, screen recording, or issue comment),
- outcome classification (`PASS`, `FAIL`, `BLOCKED`).

If a task fails, add:

- linked issue URL,
- blocker severity,
- next retry owner/date.

## Task Tracker (Owners + Evidence Fields)

| ID | Checklist Item | Primary Owner | Backup Owner | Target Date (UTC) | Environment / Tester | Evidence Link(s) | Status | Notes / Blockers |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| WIN-FTUX-01 | App launches without CLI prerequisite for normal user flow. | Erich Donahue (@edonahue) | discogs_player maintainer (@edonahue) | 2026-02-27 | Clean Windows pilot machine (pending) | docs/evidence/STEP2_MANUAL_VALIDATION_EVIDENCE_v0.2.0-rc4_2026-02-26.md#win-ftux-01 | BLOCKED | Requires Windows manual run not executable from current Linux tty environment. |
| WIN-UA-01 | Technical pilot-user path completes without blocker. | Erich Donahue (@edonahue) | discogs_player maintainer (@edonahue) | 2026-02-28 | Technical pilot user session (pending) | docs/evidence/STEP2_MANUAL_VALIDATION_EVIDENCE_v0.2.0-rc4_2026-02-26.md#win-ua-01 | BLOCKED | Technical pilot walkthrough has not been executed in this environment. |
| WIN-UA-02 | Non-technical pilot-user path completes with guided instructions only. | Erich Donahue (@edonahue) | discogs_player maintainer (@edonahue) | 2026-02-28 | Non-technical pilot user session (pending) | docs/evidence/STEP2_MANUAL_VALIDATION_EVIDENCE_v0.2.0-rc4_2026-02-26.md#win-ua-02 | BLOCKED | Non-technical pilot walkthrough has not been executed in this environment. |
| DEB-BLD-01 | Debian artifact installs on supported distro baseline. | Erich Donahue (@edonahue) | discogs_player maintainer (@edonahue) | 2026-03-01 | Linux host (`XDG_SESSION_TYPE=tty`) | docs/evidence/STEP2_MANUAL_VALIDATION_EVIDENCE_v0.2.0-rc4_2026-02-26.md#deb-bld-01 | BLOCKED | Clean-venv artifact install failed on package-index DNS lookup (`httpx`). |
| DEB-BLD-02 | Launcher integration works after install. | Erich Donahue (@edonahue) | discogs_player maintainer (@edonahue) | 2026-03-01 | Linux host (`XDG_SESSION_TYPE=tty`) | docs/evidence/STEP2_MANUAL_VALIDATION_EVIDENCE_v0.2.0-rc4_2026-02-26.md#deb-bld-02 | BLOCKED | Install wiring passed; launcher runtime validation blocked by GTK/headless constraints. |
| DEB-FTUX-01 | Plus profile install (`.[spotify]`) and auth doctor path validated. | Erich Donahue (@edonahue) | discogs_player maintainer (@edonahue) | 2026-03-01 | Linux host (`XDG_SESSION_TYPE=tty`) | docs/evidence/STEP2_MANUAL_VALIDATION_EVIDENCE_v0.2.0-rc4_2026-02-26.md#deb-ftux-01 | BLOCKED | Full plus install blocked by dependency DNS failures; `--no-deps` fallback not sufficient. |
| MAC-BLD-01 | Gatekeeper behavior documented for current signing/notarization state. | Erich Donahue (@edonahue) | discogs_player maintainer (@edonahue) | 2026-03-02 | Documentation closure (2026-02-26) | docs/evidence/STEP2_MANUAL_VALIDATION_EVIDENCE_v0.2.0-rc4_2026-02-26.md#mac-bld-01 | PASS | Gatekeeper/signing posture documented in `docs/quickstart_macos.md`. |
| MAC-BLD-02 | Future signing/notarization TODOs captured if release is unsigned. | Erich Donahue (@edonahue) | discogs_player maintainer (@edonahue) | 2026-03-02 | Documentation closure (2026-02-26) | docs/evidence/STEP2_MANUAL_VALIDATION_EVIDENCE_v0.2.0-rc4_2026-02-26.md#mac-bld-02 | PASS | Signing/notarization TODO sequence captured in `docs/quickstart_macos.md`. |

## Execution Notes By Platform

### Windows

Minimum evidence package per task:

1. install artifact identifier + checksum used,
2. launcher/start-menu or desktop launch proof without CLI usage,
3. pilot walkthrough transcript (technical and non-technical),
4. outcome notes and any blocker issue link.

### Debian Linux

Minimum evidence package per task:

1. distro and desktop-session type (not tty/headless-only),
2. clean install transcript from release artifact,
3. launcher invocation proof in real desktop session,
4. plus-profile/auth-doctor transcript and outcome.

### macOS

Minimum evidence package per task:

1. artifact provenance (tag + checksum),
2. Gatekeeper prompt/behavior documentation with screenshot/log evidence,
3. explicit statement of current signing/notarization posture,
4. TODO list for future signing/notarization closure if unsigned.

## GO/NO-GO Re-evaluation Record

- Re-evaluation date (UTC): 2026-02-26
- Decision (`GO` / `NO-GO`): NO-GO
- Decision owners: Erich Donahue (@edonahue), Engineering
- Evidence summary links:
  - `docs/evidence/STEP2_MANUAL_VALIDATION_EVIDENCE_v0.2.0-rc4_2026-02-26.md`
  - `https://github.com/edonahue/Discogs_Spinner/issues/1`
- Remaining open risks (if any):
  - Windows manual FTUX and user-acceptance walkthroughs not yet executed.
  - Debian clean desktop-session launcher runtime remains unverified in non-headless environment.
  - Debian clean install from artifact with full dependency resolution remains blocked in current DNS-restricted runtime.
