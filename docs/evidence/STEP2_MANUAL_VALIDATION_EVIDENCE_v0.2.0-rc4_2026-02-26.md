# Step 2 Manual Validation Evidence (`v0.2.0-rc4`)

Date: 2026-02-26 (UTC)
Issue tracker: `https://github.com/edonahue/Discogs_Spinner/issues/1`
Runbook: `docs/RELEASE_STEP2_MANUAL_VALIDATION_RUNBOOK_v0.2.0-rc4_2026-02-26.md`

## Environment Snapshot

- Host: Linux (`uname -a` captured during execution)
- Session: `XDG_SESSION_TYPE=tty`, `DISPLAY` unset
- Constraint: no direct Windows/macOS runtime access from this environment

## Step-Order Execution Results

### WIN-FTUX-01

- Outcome: `BLOCKED`
- Reason: requires clean Windows machine manual launch validation (non-CLI path) not available in this Linux/tty environment.
- Evidence: runbook task status + issue tracker link.

### WIN-UA-01

- Outcome: `BLOCKED`
- Reason: requires technical pilot-user walkthrough on Windows; no remote pilot session execution path available in this environment.
- Evidence: runbook task status + issue tracker link.

### WIN-UA-02

- Outcome: `BLOCKED`
- Reason: requires non-technical pilot-user guided walkthrough on Windows; no pilot-user session executed from this environment.
- Evidence: runbook task status + issue tracker link.

### DEB-BLD-01

- Outcome: `BLOCKED`
- Environment: Linux host in tty/headless session.
- Execution: clean venv install from release artifact wheel.
- Result: dependency resolution to package index failed (`httpx` not resolvable due DNS failure).
- Logs:
  - `docs/evidence/v0.2.0-rc4-step2-2026-02-26/core_install.txt`
  - `docs/evidence/v0.2.0-rc4-step2-2026-02-26/plus_install.txt`

### DEB-BLD-02

- Outcome: `BLOCKED` (install wiring pass, runtime validation blocked)
- Environment: Linux host in tty/headless session.
- Execution:
  - launcher installation script executed successfully into isolated XDG paths,
  - launcher runtime attempted directly and with `xvfb-run`.
- Result:
  - install wiring: pass,
  - runtime: failed due missing GTK bindings and headless runtime constraints.
- Logs:
  - `docs/evidence/v0.2.0-rc4-step2-2026-02-26/launcher_install.txt`
  - `docs/evidence/v0.2.0-rc4-step2-2026-02-26/launcher_run_direct.txt`
  - `docs/evidence/v0.2.0-rc4-step2-2026-02-26/launcher_run_xvfb.txt`

### DEB-FTUX-01

- Outcome: `BLOCKED`
- Environment: Linux host in tty/headless session.
- Execution:
  - plus-profile install from artifact failed on dependency DNS resolution,
  - fallback `--no-deps` install succeeded, but `auth spotify-doctor --json` failed (missing `typer`).
- Result: full clean plus-profile validation remains incomplete.
- Logs:
  - `docs/evidence/v0.2.0-rc4-step2-2026-02-26/plus_install.txt`
  - `docs/evidence/v0.2.0-rc4-step2-2026-02-26/plus_install_nodeps.txt`
  - `docs/evidence/v0.2.0-rc4-step2-2026-02-26/plus_spotify_doctor_nodeps.txt`

### MAC-BLD-01

- Outcome: `PASS` (documentation closure)
- Execution: documented current Gatekeeper/signing posture for unsigned RC distribution.
- Evidence:
  - `docs/quickstart_macos.md` (`Gatekeeper and Signing Status (2026-02-26)` section)

### MAC-BLD-02

- Outcome: `PASS` (documentation closure)
- Execution: captured explicit signing/notarization TODO sequence for future closure.
- Evidence:
  - `docs/quickstart_macos.md` (`Signing/Notarization TODOs` section)

## Decision Snapshot

- As of 2026-02-26 UTC, unresolved Windows and Debian manual validations keep rollout decision at `NO-GO` beyond pilot cohort.
