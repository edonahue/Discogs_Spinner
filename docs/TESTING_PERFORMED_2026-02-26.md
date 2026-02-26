# Testing Performed (2026-02-26)

Date: 2026-02-26 (UTC)  
Context: Release-readiness validation evidence for checkpoint/docs updates and `v0.2.0-rc4` pipeline stabilization.

## Validation Pass A (Checkpoint Baseline)

Commands run:

```bash
bash ./scripts/prepublish_hygiene_check.sh
venv/bin/ruff check .
venv/bin/python -m mypy src/discogs_player --show-error-codes --hide-error-context
venv/bin/python -m pytest -q
npm --prefix webapp run build
```

Results:

- `prepublish_hygiene_check.sh`: PASS
- `ruff check .`: PASS (`All checks passed!`)
- `mypy`: PASS (`Success: no issues found in 92 source files`)
- `pytest -q`: PASS (`369 passed, 3 skipped`)
- `npm --prefix webapp run build`: PASS (Vite production build completed)

## Validation Pass B (RC4 Follow-Up)

Commands run:

```bash
bash ./scripts/prepublish_hygiene_check.sh
venv/bin/ruff check .
venv/bin/python -m mypy src/discogs_player --show-error-codes --hide-error-context
venv/bin/python -m pytest -q
npm --prefix webapp run build
./scripts/gui_smoke_test.sh 12
./scripts/gallery_ux_smoke.sh 12
```

Results:

- `prepublish_hygiene_check.sh`: PASS
- `ruff check .`: PASS (`All checks passed!`)
- `mypy`: PASS (`Success: no issues found in 92 source files`)
- `pytest -q`: PASS (`369 passed, 3 skipped in 43.46s`)
- `npm --prefix webapp run build`: PASS
- `./scripts/gui_smoke_test.sh 12`: PASS (`ok: true`)
- `./scripts/gallery_ux_smoke.sh 12`: PASS (`ok: true`)

## Validation Pass C (Checklist Continuation)

Commands run:

```bash
PIP_NO_BUILD_ISOLATION=1 PIP_WHEEL_NO_DEPS=1 ./scripts/build_artifacts.sh core
PIP_NO_BUILD_ISOLATION=1 PIP_WHEEL_NO_DEPS=1 ./scripts/build_artifacts.sh plus
venv/bin/python -m discogs_player.main setup --json
venv/bin/python -m discogs_player.main sync
venv/bin/python -m discogs_player.main status --json
venv/bin/python -m discogs_player.main list --limit 5 --json
venv/bin/python -m discogs_player.main spin --json
venv/bin/python -m discogs_player.main auth spotify-doctor --json
venv/bin/python -m discogs_player.main devices --json
./scripts/gui_smoke_test.sh 12
./scripts/gallery_ux_smoke.sh 12
```

Results:

- Artifact rebuild: PASS for `core` and `plus` (fresh Linux tarballs include wheel + install text).
- Core workflow commands: PASS (`setup`, `sync`, `status`, `list`, `spin`).
- Plus diagnostics path: PASS (`auth spotify-doctor --json`).
- Device listing call: PASS (`devices --json` returned empty list in this environment).
- GUI smoke scripts: PASS (`ok: true` for both smoke scripts).

Blocking observations:

- Clean-venv install from generated artifact wheels failed in this shell environment because `pip` dependency resolution to package index failed (`Could not find a version that satisfies the requirement httpx<1.0,>=0.27` after DNS resolution errors).
- Launcher install script created desktop entry/launcher/icon as expected in isolated XDG paths, but launcher runtime smoke under this headless sandbox exited non-zero with `Gtk couldn't be initialized`.

## Validation Pass D (All-3 Execution Gates)

Context: user-requested execution of all three next steps with full testing between each.

Full matrix command set (run three times: pre-push, post-push, pre-go/no-go):

```bash
bash ./scripts/prepublish_hygiene_check.sh
venv/bin/ruff check .
venv/bin/python -m mypy src/discogs_player --show-error-codes --hide-error-context
venv/bin/python -m pytest -q
npm --prefix webapp run build
./scripts/gui_smoke_test.sh 12
./scripts/gallery_ux_smoke.sh 12
venv/bin/python -m sphinx -b html docs/source /tmp/discogs_player_sphinx_build
```

Results:

- All three full matrix passes: PASS.
- `pytest` each run: `369 passed, 3 skipped`.

Debian desktop-session validation commands run during this window:

```bash
python3 -m venv /tmp/.../core/.venv && /tmp/.../core/.venv/bin/pip install dist/artifacts/linux-x86_64/core-wheel.whl
python3 -m venv /tmp/.../plus/.venv && /tmp/.../plus/.venv/bin/pip install dist/artifacts/linux-x86_64/plus-wheel.whl
XDG_DATA_HOME=/tmp/... INSTALL_BIN_DIR=/tmp/... ./scripts/install_desktop_app.sh
/tmp/.../discogs-player-gui --smoke-test --limit 12
xvfb-run -a /tmp/.../discogs-player-gui --smoke-test --limit 12
XDG_DATA_HOME=/tmp/... INSTALL_BIN_DIR=/tmp/... ./scripts/uninstall_desktop_app.sh
```

Results:

- Clean artifact installs (core/plus): FAIL in this environment due DNS resolution failures to package index dependencies (`httpx`).
- Launcher integration wiring (install/uninstall): PASS.
- Launcher runtime smoke (direct + `xvfb`): FAIL (`Gtk couldn't be initialized`) in this tty/headless sandbox runtime.

## Validation Pass E (Windows/macOS Pilot Automation Kickoff)

Commands run:

```bash
venv/bin/ruff check scripts/ci_pilot_validation.py
venv/bin/python -m py_compile scripts/ci_pilot_validation.py
venv/bin/python -m pytest -q tests/test_core_plus_ci_workflow.py tests/test_tagged_release_workflow.py
git push git@github.com:edonahue/Discogs_Spinner.git master:master
```

Results:

- New workflow added: `.github/workflows/pilot_validation_windows_macos.yml` (clean-runner validation on `windows-latest` + `macos-latest`).
- New validation harness added: `scripts/ci_pilot_validation.py`.
- Lint/compile/workflow tests: PASS.
- Push trigger: PASS (`4390aca..2a682e4  master -> master`).

Blocking observation:

- Follow-up status polling for the triggered run could not be captured from this shell due DNS resolution failure to GitHub hosts (`github.com`, `api.github.com`) at validation time.

## Validation Pass F (Windows/macOS Pilot Workflow Result)

Result confirmation:

- Workflow `Pilot Validation (Windows/macOS)` outcome for the triggered clean-runner validation was confirmed as **PASS**.

Coverage confirmed by that workflow:

- Build artifacts on `windows-latest` and `macos-latest`.
- Clean profile command-path checks from built artifacts:
  - `setup --json`,
  - `status --json`,
  - `sync` (expected missing-token path),
  - `list --json`,
  - `spin --json`,
  - `play --open --json`,
  - `auth spotify-doctor --json`,
  - `devices --json` (success or expected missing-token guidance).

## Release Automation Evidence

- `v0.2.0-rc2` tagged-release run: failed on macOS artifact step
- `v0.2.0-rc3` tagged-release run: failed on macOS artifact step
- `v0.2.0-rc4` tagged-release run: all jobs succeeded
  - Run: `https://github.com/edonahue/Discogs_Spinner/actions/runs/22426315828`
