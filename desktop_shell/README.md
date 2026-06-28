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
| `src-tauri/tauri.conf.json` | Complete — bundle enabled, sidecar registered |
| `src-tauri/` | Scaffolded — Cargo.toml, main.rs, lib.rs, capabilities |
| Sidecar build | `scripts/build_sidecar.sh` — PyInstaller, per-platform |
| GTK4 .deb build | `scripts/build_deb.sh` — fpm-based, build wheelhouse with Python 3.10 |
| CI workflow | `.github/workflows/installer_build.yml` |
| Icons | In place — generated with `cargo tauri icon` |
| Code signing | **Deferred** — ship unsigned first (see Phase E in plan) |

## Prerequisites before `cargo tauri build`

1. **Sidecar binary** must be present in `binaries/` (built by `build_sidecar.sh`).
   Validate with:
   ```
   python3 ../../scripts/validate_tauri_sidecar_contract.py \
     --target-triple x86_64-unknown-linux-gnu \
     --require-file --check-executable
   ```
2. **React dist** must be present in `../../webapp/dist` (run `npm run build` in `webapp/`).
3. **Icons** must be present in `../icons/` — generate with:
   ```
   cargo tauri icon ../../assets/icons/discogs-player.svg
   ```
   (requires Tauri CLI v2: `cargo install tauri-cli --version "^2" --locked`)

## Quick local build (Linux)

```bash
# 1. Build Python sidecar
./scripts/build_sidecar.sh

# 2. Build React webapp
cd webapp && npm run build && cd ..

# 3. Generate icons
cd desktop_shell/src-tauri
cargo tauri icon ../../assets/icons/discogs-player.svg

# 4. Build installers
cargo tauri build --bundles deb,appimage

# 5. Validate Linux bundle contents
bash ../scripts/validate_tauri_linux_bundle.sh \
  --target-triple x86_64-unknown-linux-gnu
```

## Real bundle validation

For a real Linux installer build gate on a host with Rust and the Linux Tauri
system libraries installed:

```bash
bash ./scripts/validate_tauri_linux_real_build.sh \
  --target-triple x86_64-unknown-linux-gnu
```

For a containerized validation path that does not rely on host Rust setup:

```bash
docker build \
  -f packaging/test/Dockerfile.tauri-linux-build \
  -t dplayer-tauri-linux-build:local \
  .
```

That Docker build performs the actual Linux sidecar build, web build, `cargo
tauri build --bundles deb,appimage`, and bundle-content validation inside an
isolated Debian Bookworm environment.

For native CI validation on the other installer targets:

```bash
bash ./scripts/validate_tauri_macos_bundle.sh \
  --target-triple aarch64-apple-darwin
```

```powershell
./scripts/validate_tauri_windows_bundle.ps1 `
  -TargetTriple x86_64-pc-windows-msvc
```

The macOS validator mounts the built `.dmg` and checks the `.app` bundle for
the packaged sidecar. The Windows validator inspects the built `.msi` and NSIS
installer with `7z` on the native GitHub runner and verifies that the bundled
`dplayer-api.exe` sidecar is present.

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

- Public release runbook: [../docs/PUBLIC_RELEASE_RUNBOOK.md](../docs/PUBLIC_RELEASE_RUNBOOK.md)
- Stable release notes: [../docs/releases/v0.2.3.md](../docs/releases/v0.2.3.md)
- Windows quickstart: [../docs/quickstart_windows.md](../docs/quickstart_windows.md)
- macOS quickstart: [../docs/quickstart_macos.md](../docs/quickstart_macos.md)
- Debian quickstart: [../docs/quickstart_debian.md](../docs/quickstart_debian.md)
- Roadmap: [../docs/CROSS_PLATFORM_IMPLEMENTATION_ROADMAP.md](../docs/CROSS_PLATFORM_IMPLEMENTATION_ROADMAP.md)
- Release checklist: [../docs/RELEASE_CHECKLIST_WINDOWS_DEBIAN_MACOS.md](../docs/RELEASE_CHECKLIST_WINDOWS_DEBIAN_MACOS.md)
- Code signing guide: [../docs/SIGNING.md](../docs/SIGNING.md)
- ADR-003: API-first local service → web app → Tauri desktop shell
