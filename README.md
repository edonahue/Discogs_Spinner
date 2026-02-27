# Discogs Spinner

> Your vinyl collection, supercharged.

<p align="center">
  <a href="https://github.com/edonahue/Discogs_Spinner/actions/workflows/core_plus_ci.yml"><img alt="Core Plus CI" src="https://github.com/edonahue/Discogs_Spinner/actions/workflows/core_plus_ci.yml/badge.svg"></a>
  <a href="https://github.com/edonahue/Discogs_Spinner/actions/workflows/pilot_validation_windows_macos.yml"><img alt="Pilot Validation" src="https://github.com/edonahue/Discogs_Spinner/actions/workflows/pilot_validation_windows_macos.yml/badge.svg"></a>
  <a href="https://github.com/edonahue/Discogs_Spinner/releases"><img alt="Release" src="https://img.shields.io/github/v/release/edonahue/Discogs_Spinner?include_prereleases"></a>
  <img alt="Python >=3.10" src="https://img.shields.io/badge/python-3.10%2B-2f5d8a">
</p>

<p align="center">
  <img src="docs/media/gif/product-demo.gif" alt="Discogs Spinner product demo" width="100%">
</p>

Discogs-first CLI and desktop app for vinyl collectors. Browse your collection, spin a random pick, and track market value — all stored locally, no subscription required.

> **Playback note:** Discogs Spinner does not stream audio. It controls playback in external apps (e.g. Spotify Connect).

---

## What You Get

- **Browse & Spin** — gallery, carousel, or text-menu view with a one-click random pick
- **Market Value Tracking** — price history, snapshot diffs, and value movers
- **Wantlist Management** — priority signals, opportunity comparisons, and filtered views
- **Spotify Control** *(optional)* — play directly via Spotify Connect from any view
- **CLI-first & SSH-ready** — every workflow available from `dplayer` in a terminal

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

---

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .

export DISCOGS_TOKEN="your_discogs_personal_token"

dplayer setup
dplayer sync
dplayer spin
dplayer play --open
```

Optional Spotify addon:

```bash
pip install -e ".[spotify]"
dplayer auth spotify-doctor
```

---

## OS Quickstarts

- [Windows Quickstart](docs/quickstart_windows.md)
- [Debian Quickstart](docs/quickstart_debian.md)
- [macOS Quickstart](docs/quickstart_macos.md)

---

## Docs

Technical references:

- [Web App README](webapp/README.md)
- [Desktop Shell README](desktop_shell/README.md)
- [Cross-Platform Implementation Roadmap](docs/CROSS_PLATFORM_IMPLEMENTATION_ROADMAP.md)
- [Architecture ADRs](docs/adr/001-layered-architecture.md)

Product goals:

- [Product State](PRODUCT_STATE.md)
- [Stabilization Backlog (2026 Q1)](STABILIZATION_BACKLOG_2026Q1.md)
- [Stabilization Execution Tracker](docs/STABILIZATION_EXECUTION_2026Q1.md)
- [Status Checkpoint (2026-02-26)](docs/STATUS_CHECKPOINT_2026-02-26.md)

Release:

- [Testing Performed (2026-02-26)](docs/TESTING_PERFORMED_2026-02-26.md)
- [Release Checklist Status (`v0.2.0-rc4`)](docs/RELEASE_CHECKLIST_STATUS_v0.2.0-rc4_2026-02-26.md)
- [RC Release Runbook](docs/RC_RELEASE_RUNBOOK.md)
- [Release Notes (v0.2.0-rc5)](docs/releases/v0.2.0-rc5.md)

---

## Contributing & Legal

- [Contributing](CONTRIBUTING.md)
- [LICENSE](LICENSE)
- [PRIVACY.md](PRIVACY.md)
- [TERMS.md](TERMS.md)
- [TRADEMARKS.md](TRADEMARKS.md)
- [COMPLIANCE.md](COMPLIANCE.md)

---

> Repository name: `Discogs_Spinner` | Package/CLI: `discogs_player` / `dplayer`
