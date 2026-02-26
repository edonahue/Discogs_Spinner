# Step 2 Manual Validation Runbook (`v0.2.0-rc4`)

Date opened: 2026-02-26 (UTC)  
Owner: Engineering  
Status: Open

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
| WIN-FTUX-01 | App launches without CLI prerequisite for normal user flow. | TBD | TBD | TBD | TBD | TBD | OPEN | Source: Stage 1 -> FTUX |
| WIN-UA-01 | Technical pilot-user path completes without blocker. | TBD | TBD | TBD | TBD | TBD | OPEN | Source: Stage 1 -> User Acceptance |
| WIN-UA-02 | Non-technical pilot-user path completes with guided instructions only. | TBD | TBD | TBD | TBD | TBD | OPEN | Source: Stage 1 -> User Acceptance |
| DEB-BLD-01 | Debian artifact installs on supported distro baseline. | TBD | TBD | TBD | TBD | TBD | OPEN | Source: Stage 2 -> Build and Artifact |
| DEB-BLD-02 | Launcher integration works after install. | TBD | TBD | TBD | TBD | TBD | OPEN | Source: Stage 2 -> Build and Artifact |
| DEB-FTUX-01 | Plus profile install (`.[spotify]`) and auth doctor path validated. | TBD | TBD | TBD | TBD | TBD | OPEN | Source: Stage 2 -> FTUX |
| MAC-BLD-01 | Gatekeeper behavior documented for current signing/notarization state. | TBD | TBD | TBD | TBD | TBD | OPEN | Source: Stage 3 -> Build and Artifact |
| MAC-BLD-02 | Future signing/notarization TODOs captured if release is unsigned. | TBD | TBD | TBD | TBD | TBD | OPEN | Source: Stage 3 -> Build and Artifact |

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

- Re-evaluation date (UTC): TBD
- Decision (`GO` / `NO-GO`): TBD
- Decision owners: TBD
- Evidence summary links: TBD
- Remaining open risks (if any): TBD
