# Current Audit Validation - 2026-04-27

Scope: local checkout, Pop!_OS/COSMIC launcher state, public GitHub release
alignment, documentation, and test coverage after recent UI/value changes.

## Repository And Release State

- Local `main` is synced with `origin/main` at `f1c2f1c`.
- Latest public GitHub release is `v0.2.0`.
- Public release assets include GTK `.deb`, Tauri `.deb`, AppImage, Windows
  MSI/EXE, macOS DMGs, and installer checksums.
- The local desktop launcher points at this checkout, but the user-level CLI
  metadata reported `0.1.0` during audit. Refresh the local install/launcher
  before treating this machine as packaged-installer evidence.

## Initial Findings

- `pytest`: `622 passed, 5 skipped`
- `npm --prefix webapp run build`: passed
- `npm --prefix webapp run test:e2e`: failed because `/value/gems` was not
  mocked and the Value page treated that optional fetch as fatal
- `venv/bin/python -m ruff check .`: failed on unused imports
- `venv/bin/python -m mypy src/discogs_player --show-error-codes --hide-error-context`:
  failed on value/hidden-gems coercion and GTK dynamic-base typing
- `./scripts/gui_smoke_test.sh 12`: passed
- `./scripts/gallery_ux_smoke.sh 12`: hung without deterministic timeout

## Post-Remediation Results

- `pytest` with system Python: `623 passed, 5 skipped`
- `venv/bin/python -m pytest`: `647 passed, 1 skipped`
- `venv/bin/python -m ruff check .`: passed
- `venv/bin/python -m mypy src/discogs_player --show-error-codes --hide-error-context`: passed
- `npm --prefix webapp run build`: passed
- `npm --prefix webapp run test:e2e`: `18 passed`
- `./scripts/gui_smoke_test.sh 12`: passed
- `./scripts/gallery_ux_smoke.sh 12`: passed
- `desktop-file-validate /home/erich/.local/share/applications/discogs-player.desktop`: passed
- `/home/erich/.local/bin/discogs-player-gui --help`: reports `Discogs Spinner GTK UI`
- `venv/bin/dplayer --version`: `0.2.0`
- `venv/bin/dplayer diagnostics --json`: reports app version `0.2.0` and live DB access works

The gallery UX smoke payload reports the configured startup target as
`1100x760`. In the headless Xvfb run, actual window height can be larger than
that target because there is no normal desktop window manager constraining the
surface; layout regression checks compare pre/post tab-return geometry in the
same runtime.

## Remaining Local Install Note

The global shell command `dplayer --version` still reports `0.1.0`. Refreshing it
with `pip install --user -e .` was blocked by the OS-managed Python environment
under PEP 668, and this audit did not force `--break-system-packages`. The
desktop launcher now uses the checkout/venv path and is aligned; the old
user-level CLI shim should be replaced through a safe installer or pipx-style
path before using bare `dplayer` as release evidence on this machine.
