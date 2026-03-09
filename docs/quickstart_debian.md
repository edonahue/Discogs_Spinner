# Quickstart (Debian Linux)

This guide targets first-time users installing `discogs_player` on Debian/Ubuntu.

## 1) Prerequisites

> **Estimated time:** ~10 minutes

- Debian 12+ (or Ubuntu equivalent)
- Discogs account + personal token ([how to get one](token_setup.md))
- Optional: Spotify account (for playback/matching features — [how to set up](token_setup.md#spotify-api-credentials))

Install system packages:

```bash
sudo apt update
sudo apt install -y \
  python3 python3-venv python3-pip python3-setuptools \
  libsecret-1-0 build-essential python3-dev
```

Optional GUI/headless smoke dependencies:

```bash
sudo apt install -y \
  python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 \
  libadwaita-1-0 gir1.2-gdkpixbuf-2.0 xvfb
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

## Option B: Portable AppImage (no install required)

Download the latest `Discogs_Spinner_*_amd64.AppImage` from the
[GitHub Releases page](https://github.com/edonahue/Discogs_Spinner/releases), then:

```bash
chmod +x Discogs_Spinner_*_amd64.AppImage
./Discogs_Spinner_*_amd64.AppImage
```

- No root required; runs from any directory.
- Handy for USB-drive installs or a display-attached server where you don't want to touch system packages.
- On Ubuntu 22.04+ you may need FUSE:
  ```bash
  sudo apt install libfuse2
  ```
- On first run, if no Discogs token is configured the app opens a Setup screen to guide you through token setup.

---

## 5) Launch the desktop GUI (optional)

> Linux only. Requires GTK4/libadwaita (installed above in prerequisites).

```bash
bash scripts/install_desktop_app.sh
```

This installs a desktop entry and launcher. Open your app launcher and search for **Discogs Player**, or run:

```bash
discogs-player-gui
```

**First-launch flow:**

- If your token is not yet set, the app shows a guided message in the status bar.
- If no sync has run yet, both Browse and Wantlist show a **Sync Collection** / **Sync Wantlist** button — click it to import your records directly from the GUI.
- Progress is shown in the status bar (`Syncing... page 3 of 12`).
- After sync, the status bar shows `Loaded N releases · Last synced YYYY-MM-DD`.

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

## Done? Verify it works

```bash
dplayer status
dplayer spin
```

If `dplayer status` shows your collection count and last sync date, you're all set.

## 7) Troubleshooting

- Run `dplayer setup` for onboarding hints.
- If playback fails, confirm a Spotify device is active and selected.
- Use issue templates for install/auth/playback reports.
