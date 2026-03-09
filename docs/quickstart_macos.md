# Quickstart (macOS)

This guide targets first-time users installing `discogs_player` on macOS.

## 1) Prerequisites

- macOS 13+
- Homebrew installed
- Discogs account + personal token ([how to get one](token_setup.md))
- Optional: Spotify account (for playback/matching features — [how to set up](token_setup.md#spotify-api-credentials))

Install base tools:

```bash
brew update
brew install python@3.12 git
```

## 2) Clone and install

```bash
git clone https://github.com/edonahue/Discogs_Spinner.git
cd Discogs_Spinner
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

Optional Spotify features:

```bash
pip install -e ".[spotify]"
```

## 3) Configure Discogs token

Get your personal access token at [discogs.com/settings/developers](https://www.discogs.com/settings/developers) (Personal Access Tokens → Generate new token).

```bash
export DISCOGS_TOKEN="your_discogs_personal_token"
dplayer setup
```

## 4) First sync and verification

```bash
dplayer sync
dplayer status
dplayer list --limit 10
```

## 5) Launch the desktop GUI (optional)

> The GTK4 desktop GUI is Linux-only. On macOS, use the CLI (`dplayer`) for all workflows.
> A native macOS app bundle is planned for a future release (see Gatekeeper section below).

All core features — sync, browse, spin, play, wantlist, analytics — are available via `dplayer` CLI on macOS.

## 6) Optional Spotify onboarding

First, create a Spotify app and get your Client ID + Secret at [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard). Add `http://127.0.0.1:8765/callback` as a redirect URI. See [token_setup.md](token_setup.md#spotify-api-credentials) for full steps.

```bash
export SPOTIPY_CLIENT_ID="your_client_id"
export SPOTIFY_SECRET="your_client_secret"
export SPOTIPY_REDIRECT_URI="http://127.0.0.1:8765/callback"
dplayer auth spotify-doctor
dplayer auth spotify --open-browser --listen-host 127.0.0.1 --listen-port 8765
dplayer devices --json
```

Safe first play fallback:

```bash
dplayer play --last-spin --open
```

## 7) Notes

- Keep this as a CLI-first setup path unless a signed macOS app build is provided.
- If browser callback fails, use manual callback options from `dplayer auth spotify --help`.

## 8) Gatekeeper and Signing Status

Current release artifacts (`.dmg`) are unsigned. Gatekeeper will block the app on first launch
with a "developer cannot be verified" warning. Clear the quarantine flag once after install:

```bash
# Option A — one-line helper (run from repo root):
bash scripts/macos_open_app.sh "/Applications/Discogs Spinner.app"

# Option B — manual:
xattr -dr com.apple.quarantine "/Applications/Discogs Spinner.app"
open "/Applications/Discogs Spinner.app"
```

> This is only required once per install. Signed builds that remove this step are planned when
> Apple Developer ID is acquired.

## 9) Signing/Notarization TODOs

1. Define signing identity and certificate storage policy for CI.
2. Add a codesign step for macOS release artifacts in tagged-release workflow.
3. Add notarization submission + staple workflow and failure handling.
4. Publish user-facing Gatekeeper troubleshooting section once signed builds ship.
