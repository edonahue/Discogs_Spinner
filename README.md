# Discogs Spinner

> Pick what to play, rediscover your shelves, and understand what your records are worth.

<p align="center">
  <a href="https://github.com/edonahue/Discogs_Spinner/actions/workflows/core_plus_ci.yml"><img alt="Core Plus CI" src="https://github.com/edonahue/Discogs_Spinner/actions/workflows/core_plus_ci.yml/badge.svg"></a>
  <a href="https://github.com/edonahue/Discogs_Spinner/actions/workflows/installer_build.yml"><img alt="Installer Build" src="https://github.com/edonahue/Discogs_Spinner/actions/workflows/installer_build.yml/badge.svg"></a>
  <a href="https://github.com/edonahue/Discogs_Spinner/releases/latest"><img alt="Latest Stable Release" src="https://img.shields.io/github/v/release/edonahue/Discogs_Spinner"></a>
  <a href="https://snapcraft.io/spinner-for-discogs"><img alt="Snap Store" src="https://snapcraft.io/spinner-for-discogs/badge.svg"></a>
  <img alt="Python 3.10+" src="https://img.shields.io/badge/python-3.10%2B-2f5d8a">
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-green"></a>
  <img alt="Platforms" src="https://img.shields.io/badge/platform-Linux%20%7C%20Windows%20%7C%20macOS-blue">
</p>

<p align="center">
  <img src="docs/media/gif/product-demo.gif" alt="Discogs Spinner product demo" width="100%">
</p>

Discogs Spinner is a local-first desktop companion for vinyl collectors who already keep a Discogs collection. Install it, connect your Discogs personal access token, sync once, then browse your shelf, spin a random record, inspect market value, and keep wantlist context close without living in browser tabs.

_Part of my [Open Workbench](https://erichdonahue.com/workbench); featured on [erichdonahue.com/music](https://erichdonahue.com/music)._

> **Playback note:** Discogs Spinner does not stream audio. It controls playback in external apps (e.g. Spotify Connect).
>
> **Discogs token required:** You need a Discogs account and a personal access token so the app can read your collection, wantlist, and market data. [Get the token setup steps →](docs/token_setup.md)
>
> **Release note:** The download links below point to the latest stable public release, `v0.2.2`. The Snap Store listing is live for Linux users who prefer a software-store install path.

---

## Why Discogs Spinner?

Your Discogs collection probably lives in a browser tab today. You scroll when you cannot decide what to play, check market prices in another tab, and open yet another app when you finally choose. Discogs Spinner turns that daily collector loop into one focused utility: your collection, random picks, wantlist context, and market value in one local app. No subscription. No extra cloud account. Just your records on your machine.

Use it when you want to:

- choose tonight's record without scrolling forever
- find neglected albums, hidden gems, and stale market values
- see whether a wantlist item is worth chasing
- keep a quick local dashboard of collection health and value
- hand a selected release off to Spotify or YouTube Music when optional playback is configured

---

## What You Get

- **Browse & Spin** — gallery, carousel, or text-menu view with a one-click random pick that honors your current filters
- **Collection Summary** — LP/45 counts, median collection value, and most-recently-added context on the browse surface
- **Market Value Tracking** — price history, snapshot diffs, value movers, a refresh priority queue (`dplayer value queue`), and a market value dashboard
- **Value Workspace** — search synced releases, inspect selected-release value detail, and jump from Browse to Value with the selected release carried over
- **Wantlist Management** — priority signals, opportunity comparisons, and filtered views
- **Tracklist at a Glance** — cached track lists in the detail panel and in a quick-view modal, no round trip to Discogs
- **Playback Control** *(optional)* — Spotify Connect or YouTube Music (native album search with browser handoff)
- **Setup Wizard** — first-run token configuration, no terminal required
- **CLI-first & SSH-ready** — every workflow available from `dplayer` in a terminal

### Power Tools

- **Analytics & Recent pages** (web) — collection trends and a recently-added view
- **Hidden Gems** — value + scarcity signals for owned releases that may deserve attention
- **Cache management** — `dplayer cache stats | prune | warm` to inspect, trim, or pre-fetch cover art
- **Share & export** — `dplayer share collection | value` emits CSV or Markdown for pasting into notes, issues, or spreadsheets
- **Match audit & review queue** — `dplayer review` workflow for approving Spotify / YouTube Music album matches in bulk
- **Collection Health scoring** — `dplayer health` to spot mapping gaps and staleness

---

## First 10 Minutes

Before launching, have this ready:

- a Discogs account with a collection or wantlist
- a Discogs personal access token from [Settings → Developers](https://www.discogs.com/settings/developers)
- optional Spotify credentials only if you want playback control

Your first run should look like this:

1. Install the app for your OS.
2. Open Discogs Spinner and paste your Discogs token into the setup wizard.
3. Start the first sync.
4. Browse your collection, hit **Spin**, and inspect the selected record.
5. Check Value, Wantlist, or Insights when you want market and collection context.

## Daily Collector Loop

After setup, the daily flow should stay simple:

1. **Sync occasionally** (`dplayer sync`) to keep collection + wantlist fresh
2. **Pick something quickly** (`dplayer spin` or native/web browse)
3. **Check context** (value, hidden gems, health, wantlist pressure)
4. **Play or open** (`dplayer play --last-spin --open`) if optional playback is connected

If you prefer a compact terminal briefing, run:

```bash
dplayer insights
```

---

## What Works Without Spotify

Spotify (and other playback providers) are optional.

Without Spotify configured, you still get:

- full Discogs collection + wantlist sync
- browse, filters, and spin workflows
- value dashboard, hidden gems, and health scoring
- local cache and export/share tooling
- provider readiness + setup diagnostics for optional integrations

You only lose direct playback control handoff until an optional provider is connected.

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

## Download Now

These installers are meant to get a collector to value quickly: install, paste a Discogs token, sync, browse, and spin.

- [Open the latest stable release page](https://github.com/edonahue/Discogs_Spinner/releases/latest)
- Windows: use the guided installer first: [Discogs Spinner_0.2.2_x64-setup.exe](https://github.com/edonahue/Discogs_Spinner/releases/download/v0.2.2/Discogs.Spinner_0.2.2_x64-setup.exe). Use [Discogs Spinner_0.2.2_x64_en-US.msi](https://github.com/edonahue/Discogs_Spinner/releases/download/v0.2.2/Discogs.Spinner_0.2.2_x64_en-US.msi) only if you specifically want MSI deployment tooling.
- macOS: download the `.dmg` that matches your Mac, then drag **Discogs Spinner** into `/Applications`: [Apple Silicon](https://github.com/edonahue/Discogs_Spinner/releases/download/v0.2.2/Discogs.Spinner_0.2.2_aarch64.dmg) or [Intel](https://github.com/edonahue/Discogs_Spinner/releases/download/v0.2.2/Discogs.Spinner_0.2.2_x64.dmg).
- Linux via Snap Store: [install Spinner for Discogs from Snapcraft](https://snapcraft.io/spinner-for-discogs), or run `sudo snap install spinner-for-discogs` if `snapd` is already set up.
- Debian/Ubuntu direct package: [discogs-spinner-gtk4_0.2.2_amd64.deb](https://github.com/edonahue/Discogs_Spinner/releases/download/v0.2.2/discogs-spinner-gtk4_0.2.2_amd64.deb).
- Linux portable fallback: [Discogs Spinner_0.2.2_amd64.AppImage](https://github.com/edonahue/Discogs_Spinner/releases/download/v0.2.2/Discogs.Spinner_0.2.2_amd64.AppImage).
- Linux alternate desktop build: [discogs-spinner-tauri_0.2.2_amd64.deb](https://github.com/edonahue/Discogs_Spinner/releases/download/v0.2.2/discogs-spinner-tauri_0.2.2_amd64.deb).
- Verify downloads with [CHECKSUMS-INSTALLERS.txt](https://github.com/edonahue/Discogs_Spinner/releases/download/v0.2.2/CHECKSUMS-INSTALLERS.txt).

What first launch should feel like:

- The app opens into a simple setup wizard if no Discogs token is configured yet.
- You paste your token once, start your first sync, and wait for the collection view to load.
- A good first run ends with your records visible, a working **Spin** button, and clear next steps for optional playback.

Quick install notes:

- Windows may show a SmartScreen warning until code signing is added.
- macOS builds are currently unsigned and may require a one-time Gatekeeper approval step.
- Linux users should start with the Snap Store when available; the GTK `.deb`, Tauri `.deb`, and AppImage remain direct-download fallbacks.

Sending this to a friend?

- Use the [Friend Trial Guide](docs/friend_trial.md) for the shortest install/setup checklist.
- Use the [Friend Trial Checklist](docs/friend_trial_checklist.md) for a fast pass/fail validation run.
- Ask them to report install, setup, or playback friction with OS, installer used, exact warning text, and a screenshot if possible.
- GitHub issue templates: [install](https://github.com/edonahue/Discogs_Spinner/issues/new?template=install_failure.yml), [auth/setup](https://github.com/edonahue/Discogs_Spinner/issues/new?template=auth_failure.yml), [playback](https://github.com/edonahue/Discogs_Spinner/issues/new?template=playback_failure.yml)

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
> Start with the native installer quickstart for your OS. Use the web quickstart only if you want a browser-based fallback instead of the installed app.

- [Not sure where to start? → START HERE](docs/START_HERE.md)
- [Windows Quickstart](docs/quickstart_windows.md)
- [Debian Quickstart](docs/quickstart_debian.md)
- [macOS Quickstart](docs/quickstart_macos.md)
- [Web App Quickstart](docs/quickstart_web.md)
- [Token Setup (Discogs + Spotify)](docs/token_setup.md)
- [Friend Trial Guide](docs/friend_trial.md)
- [Friend Trial Checklist](docs/friend_trial_checklist.md)
- [Windows + WSL2 GUI Quickstart](docs/quickstart_wsl2.md)

---

## Help & Reference

- [Release Notes (v0.2.2)](docs/releases/v0.2.2.md)
- [Support Matrix](docs/SUPPORT_MATRIX.md)
- [Report a bug or request a feature](https://github.com/edonahue/Discogs_Spinner/issues)

<details>
<summary>Developer Docs</summary>

- [Web App README](webapp/README.md)
- [Desktop Shell README](desktop_shell/README.md)
- [Architecture ADRs](docs/adr/001-layered-architecture.md)

</details>

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
