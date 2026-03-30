# Discogs Spinner

> Your vinyl collection, supercharged.

<p align="center">
  <a href="https://github.com/edonahue/Discogs_Spinner/actions/workflows/core_plus_ci.yml"><img alt="Core Plus CI" src="https://github.com/edonahue/Discogs_Spinner/actions/workflows/core_plus_ci.yml/badge.svg"></a>
  <a href="https://github.com/edonahue/Discogs_Spinner/actions/workflows/installer_build.yml"><img alt="Installer Build" src="https://github.com/edonahue/Discogs_Spinner/actions/workflows/installer_build.yml/badge.svg"></a>
  <a href="https://github.com/edonahue/Discogs_Spinner/releases"><img alt="Release" src="https://img.shields.io/github/v/release/edonahue/Discogs_Spinner?include_prereleases"></a>
  <img alt="Python 3.10+" src="https://img.shields.io/badge/python-3.10%2B-2f5d8a">
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-green"></a>
  <img alt="Platforms" src="https://img.shields.io/badge/platform-Linux%20%7C%20Windows%20%7C%20macOS-blue">
</p>

<p align="center">
  <img src="docs/media/gif/product-demo.gif" alt="Discogs Spinner product demo" width="100%">
</p>

Discogs-first collector app for vinyl fans who want native installers on Linux, Windows, and macOS. Browse your collection, spin a random pick, and track market value locally, with no subscription required.

> **Playback note:** Discogs Spinner does not stream audio. It controls playback in external apps (e.g. Spotify Connect).

---

## Why Discogs Spinner?

Your Discogs collection lives in a browser tab. You scroll it when you can't decide what to spin,
squint at market prices in a second tab, and open Spotify in a third. Discogs Spinner pulls all
of that into one place — a local app that knows your collection, picks records for you, shows you
what they're worth today, and queues them up in Spotify with one command. No cloud account. No
subscription. Runs on your machine.

---

## What You Get

- **Browse & Spin** — gallery, carousel, or text-menu view with a one-click random pick
- **Market Value Tracking** — price history, snapshot diffs, value movers, a refresh priority queue (`dplayer value queue`), and a market value dashboard
- **Collection Health** — scored summary of mapping coverage and staleness (`dplayer health`)
- **Wantlist Management** — priority signals, opportunity comparisons, and filtered views
- **Playback Control** *(optional)* — Spotify Connect or YouTube Music (open-in-browser)
- **Setup Wizard** — first-run token configuration, no terminal required
- **CLI-first & SSH-ready** — every workflow available from `dplayer` in a terminal

---

## Three Ways to Use

| Mode | Launch | Best for |
|------|--------|----------|
| **Native app** | Installed desktop app | Windows, macOS, Linux desktop users |
| **CLI** | `dplayer` | Terminal users, SSH, scripting |
| **Web App** | `dplayer-api` then open browser | Browser-first setups on any OS |

---

## Screenshots

<p align="center">
  <img src="docs/media/screenshots/01-browse-gallery.png" alt="Browse — gallery view with album art grid" width="49%">
  <img src="docs/media/screenshots/02-spin-result.png" alt="Browse — carousel with album detail, market data, and tracklist" width="49%">
</p>
<p align="center"><em>Browse gallery &nbsp;·&nbsp; Album detail after spin</em></p>

<p align="center">
  <img src="docs/media/screenshots/03-market-value-dashboard.png" alt="Collection Value Dashboard — total, median, top movers" width="49%">
  <img src="docs/media/screenshots/04-wantlist-view.png" alt="Wantlist gallery view with cover art" width="49%">
</p>
<p align="center"><em>Collection Value Dashboard &nbsp;·&nbsp; Wantlist gallery</em></p>

<p align="center">
  <img src="docs/media/screenshots/05-setup-wizard.png" alt="Setup Wizard — first-run Discogs token configuration" width="49%">
</p>
<p align="center"><em>Setup Wizard — first-run token configuration</em></p>

---

## Install Fast

- Windows: download the latest `.msi` or `-setup.exe` from [GitHub Releases](https://github.com/edonahue/Discogs_Spinner/releases), run it, and finish the in-app setup wizard.
- macOS: download the latest `.dmg` from [GitHub Releases](https://github.com/edonahue/Discogs_Spinner/releases), drag **Discogs Spinner** into `/Applications`, then launch it once and clear Gatekeeper quarantine if prompted.
- Debian/Ubuntu: install the GTK `.deb` or use the `.AppImage` from [GitHub Releases](https://github.com/edonahue/Discogs_Spinner/releases).

Need the terminal-first path instead?

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

export DISCOGS_TOKEN="your_discogs_personal_token"

dplayer setup
dplayer sync
dplayer spin
dplayer play --open
```

Need a token? [Get your Discogs personal access token →](docs/token_setup.md)

Optional Spotify addon:

```bash
pip install -e ".[spotify]"
dplayer auth spotify-doctor
```

Need Spotify credentials? [Set up Spotify API access →](docs/token_setup.md#spotify-api-credentials)

---

## OS Quickstarts

> **New here?**
> - Easiest native install: [Windows Quickstart](docs/quickstart_windows.md), [macOS Quickstart](docs/quickstart_macos.md), or [Debian Quickstart](docs/quickstart_debian.md)
> - Easiest browser-based start: [Web App Quickstart](docs/quickstart_web.md) (Windows / macOS / Linux)
> - Linux desktop: [Debian Quickstart](docs/quickstart_debian.md)
> - Windows native installer: [Windows Quickstart](docs/quickstart_windows.md)
> - macOS native installer: [macOS Quickstart](docs/quickstart_macos.md)

- [Not sure where to start? → START HERE](docs/START_HERE.md)
- [Windows Quickstart](docs/quickstart_windows.md)
- [Windows + WSL2 GUI Quickstart](docs/quickstart_wsl2.md)
- [Debian Quickstart](docs/quickstart_debian.md)
- [macOS Quickstart](docs/quickstart_macos.md)
- [Web App Quickstart](docs/quickstart_web.md)
- [Token Setup (Discogs + Spotify)](docs/token_setup.md)

---

## Docs

Technical references:

- [Web App README](webapp/README.md)
- [Desktop Shell README](desktop_shell/README.md)
- [Code Signing Guide](docs/SIGNING.md)
- [Architecture ADRs](docs/adr/001-layered-architecture.md)

<details>
<summary>Project & release docs</summary>

- [Product State](PRODUCT_STATE.md)
- [Cross-Platform Implementation Roadmap](docs/CROSS_PLATFORM_IMPLEMENTATION_ROADMAP.md)
- [Stabilization Execution Tracker](docs/STABILIZATION_EXECUTION_2026Q1.md)
- [Public Release Runbook](docs/PUBLIC_RELEASE_RUNBOOK.md)
- [Release Notes (v0.2.0)](docs/releases/v0.2.0.md)

</details>

---

## Contributing & Legal

- [Contributing](CONTRIBUTING.md)
- [Report a bug or request a feature](https://github.com/edonahue/Discogs_Spinner/issues)
- [LICENSE](LICENSE)
- [PRIVACY.md](PRIVACY.md)
- [TERMS.md](TERMS.md)
- [TRADEMARKS.md](TRADEMARKS.md)
- [COMPLIANCE.md](COMPLIANCE.md)

---

> Repository name: `Discogs_Spinner` | Package/CLI: `discogs_player` / `dplayer`
