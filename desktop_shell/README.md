# Discogs Spinner — Desktop Shell

Tauri v2 desktop packaging shell for cross-platform GUI distribution.

## Architecture

```
[Tauri shell]
  ├── Webview  → webapp/dist  (React + Vite)
  └── Sidecar  → dplayer-api  (FastAPI, PyInstaller bundle, 127.0.0.1:8768)
```

The GTK4 GUI (`ui_main.py`) is **Linux-only** and distributed separately as a `.deb`.
Windows and macOS receive the Tauri web-UI wrapper instead.

## Current state

| Component | Status |
|-----------|--------|
| `tauri.conf.json` | Complete — bundle enabled, sidecar registered |
| `src-tauri/` | Scaffolded — Cargo.toml, main.rs, lib.rs, capabilities |
| Sidecar build | `scripts/build_sidecar.sh` — PyInstaller, per-platform |
| GTK4 .deb build | `scripts/build_deb.sh` — fpm-based |
| CI workflow | `.github/workflows/installer_build.yml` |
| Icons | In place — generated with `cargo tauri icon` |
| Code signing | **Deferred** — ship unsigned first (see Phase E in plan) |

## Prerequisites before `cargo tauri build`

1. **Sidecar binary** must be present in `src-tauri/binaries/` (built by `build_sidecar.sh`).
2. **React dist** must be present in `../webapp/dist` (run `npm run build` in `webapp/`).
3. **Icons** must be present in `src-tauri/icons/` — generate with:
   ```
   cargo tauri icon ../assets/icons/discogs-player.svg
   ```
   (requires Tauri CLI v2: `cargo install tauri-cli --version "^2" --locked`)

## Quick local build (Linux)

```bash
# 1. Build Python sidecar
./scripts/build_sidecar.sh

# 2. Build React webapp
cd webapp && npm run build && cd ..

# 3. Generate icons
cd desktop_shell
cargo tauri icon ../assets/icons/discogs-player.svg

# 4. Build installers
cargo tauri build --bundles deb,appimage
```

## First-run token flow

If `DISCOGS_TOKEN` is not set when the Tauri app launches, the React webapp automatically
redirects to `/setup`. The user enters their Discogs personal access token; the webapp
calls `POST /api/v1/setup`, which persists the token and returns the updated setup
status. On success, the app redirects to the home dashboard.

## Code signing notes (Phase E)

| Platform | Requirement | Cost |
|----------|------------|------|
| macOS | Apple Developer Program + notarization | $99/yr |
| Windows | EV Code Signing cert | ~$300–500/yr |
| Windows (interim) | Self-signed NSIS | $0 — SmartScreen warning |
| Linux | GPG-signed .deb | $0 |

Until signing is in place, end-users on macOS must run:
```
xattr -dr com.apple.quarantine "Discogs Spinner.app"
```

## Reference

- Roadmap: `../docs/CROSS_PLATFORM_IMPLEMENTATION_ROADMAP.md`
- Release checklist: `../docs/RELEASE_CHECKLIST_WINDOWS_DEBIAN_MACOS.md`
- Code signing guide: `../docs/SIGNING.md`
- ADR-003: API-first local service → web app → Tauri desktop shell
