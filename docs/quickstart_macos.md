# Quickstart (macOS)

This guide targets first-time users installing `discogs_player` on macOS.

## 1) Prerequisites

> **Estimated time:** ~5 minutes

- macOS 13+
- Discogs account + personal token ([how to get one](token_setup.md))
- Optional: Spotify account (for playback/matching features — [how to set up](token_setup.md#spotify-api-credentials))

## 2) Install the native app

Download the current stable `.dmg` directly:

- Recommended for most modern Macs: [Discogs Spinner_0.2.2_aarch64.dmg](https://github.com/edonahue/Discogs_Spinner/releases/download/v0.2.2/Discogs.Spinner_0.2.2_aarch64.dmg)
- Intel Macs: [Discogs Spinner_0.2.2_x64.dmg](https://github.com/edonahue/Discogs_Spinner/releases/download/v0.2.2/Discogs.Spinner_0.2.2_x64.dmg)
- Fallback release page: [GitHub Releases](https://github.com/edonahue/Discogs_Spinner/releases/latest)

Open the disk image, drag **Discogs Spinner.app** into `/Applications`, then launch it once.

What you may see:

- Current macOS builds are unsigned.
- If Gatekeeper blocks the first launch, clear quarantine once:

```bash
xattr -dr com.apple.quarantine "/Applications/Discogs Spinner.app"
open "/Applications/Discogs Spinner.app"
```

## 3) Configure Discogs token

On first launch, the app should open into the setup flow. Paste your Discogs personal access token, save it, then start your first sync.

## 4) First sync and verification

- Confirm the setup flow saves your token
- Start a collection sync from the app
- Confirm the collection view loads without errors

What success looks like:

- the app opens from `/Applications`
- the setup wizard accepts your Discogs token
- your first sync ends with the collection view loaded

## 5) Optional Spotify onboarding

First, create a Spotify app and get your Client ID + Secret at [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard). Add `http://127.0.0.1:8765/callback` as a redirect URI. See [token_setup.md](token_setup.md#spotify-api-credentials) for full steps.

```bash
export SPOTIPY_CLIENT_ID="your_client_id"
export SPOTIFY_SECRET="your_client_secret"
export SPOTIPY_REDIRECT_URI="http://127.0.0.1:8765/callback"
dplayer auth spotify-doctor
dplayer auth spotify --open-browser --listen-host 127.0.0.1 --listen-port 8765
dplayer devices --json
```

Safe first play fallback from the CLI:

```bash
dplayer play --last-spin --open
```

## 6) Terminal / CLI path (advanced)

If you want the Python CLI alongside the native macOS app, install it from source:

```bash
brew update
brew install python@3.12 git
git clone https://github.com/edonahue/Discogs_Spinner.git
cd Discogs_Spinner
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .
pip install -e ".[spotify]"
```

Equivalent CLI-first onboarding:

```bash
export DISCOGS_TOKEN="your_discogs_personal_token"
dplayer setup
dplayer sync
dplayer status
dplayer list --limit 10
```

## Done? Verify it works

- Native app path: the app opens, setup succeeds, and your collection loads
- CLI path: `dplayer status` shows your collection count and last sync date

For a clean-machine installer checklist, use [macOS Installer FTUX Validation](validation/macos_installer_ftux.md).

If browser callback fails during Spotify auth, use the manual callback options from `dplayer auth spotify --help`.
