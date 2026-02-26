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

## Release Automation Evidence

- `v0.2.0-rc2` tagged-release run: failed on macOS artifact step
- `v0.2.0-rc3` tagged-release run: failed on macOS artifact step
- `v0.2.0-rc4` tagged-release run: all jobs succeeded
  - Run: `https://github.com/edonahue/Discogs_Spinner/actions/runs/22426315828`
