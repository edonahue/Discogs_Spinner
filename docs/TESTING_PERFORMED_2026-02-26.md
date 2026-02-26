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

## Release Automation Evidence

- `v0.2.0-rc2` tagged-release run: failed on macOS artifact step
- `v0.2.0-rc3` tagged-release run: failed on macOS artifact step
- `v0.2.0-rc4` tagged-release run: all jobs succeeded
  - Run: `https://github.com/edonahue/Discogs_Spinner/actions/runs/22426315828`
