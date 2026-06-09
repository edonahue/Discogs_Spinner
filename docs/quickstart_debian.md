# Quickstart (Debian Linux)

This guide targets first-time users installing `discogs_player` on Linux, with Debian/Ubuntu direct packages available as fallbacks.

## 1) Prerequisites

> **Estimated time:** ~10 minutes

- Debian 12+ (or Ubuntu equivalent)
- Discogs account + personal token ([how to get one](token_setup.md))
- Optional: Spotify account (for playback/matching features — [how to set up](token_setup.md#spotify-api-credentials))

## 2) Install the Linux desktop app

### Option A: Snap Store install (recommended)

Install from the Snap Store:

```bash
sudo snap install spinner-for-discogs
```

Launch **Spinner for Discogs** from your app menu, or run:

```bash
spinner-for-discogs
```

If your distribution does not have `snapd` installed yet, use the distro-specific instructions on the [Spinner for Discogs Snap Store page](https://snapcraft.io/spinner-for-discogs).

What success looks like:

- the desktop app launches from your app menu
- the setup flow accepts your Discogs token
- your first sync ends with the collection and wantlist views loaded

### Option B: GTK desktop `.deb` installer

Download the current stable GTK `.deb` directly:

- [discogs-spinner-gtk4_0.2.2_amd64.deb](https://github.com/edonahue/Discogs_Spinner/releases/download/v0.2.2/discogs-spinner-gtk4_0.2.2_amd64.deb)
- Checksums: [CHECKSUMS-INSTALLERS.txt](https://github.com/edonahue/Discogs_Spinner/releases/download/v0.2.2/CHECKSUMS-INSTALLERS.txt)
- Fallback release page: [GitHub Releases](https://github.com/edonahue/Discogs_Spinner/releases/latest)

Then install it:

```bash
sudo apt install ./discogs-spinner-gtk4_0.2.2_amd64.deb
```

Launch **Discogs Spinner** from your app menu, or run:

```bash
dplayer-gui
```

The package also installs the CLI and API launchers:

```bash
dplayer status
```

What success looks like:

- the desktop app launches from your app menu
- the setup flow accepts your Discogs token
- your first sync ends with the collection and wantlist views loaded

### Option C: Portable AppImage (no install required)

Download the current stable AppImage directly:

- [Discogs Spinner_0.2.2_amd64.AppImage](https://github.com/edonahue/Discogs_Spinner/releases/download/v0.2.2/Discogs.Spinner_0.2.2_amd64.AppImage)
- Checksums: [CHECKSUMS-INSTALLERS.txt](https://github.com/edonahue/Discogs_Spinner/releases/download/v0.2.2/CHECKSUMS-INSTALLERS.txt)
- Fallback release page: [GitHub Releases](https://github.com/edonahue/Discogs_Spinner/releases/latest)

Then:

```bash
chmod +x Discogs.Spinner_0.2.2_amd64.AppImage
./Discogs.Spinner_0.2.2_amd64.AppImage
```

- No root required; runs from any directory.
- Handy for USB-drive installs or a display-attached server where you don't want to touch system packages.
- On Ubuntu 22.04+ you may need FUSE:
  ```bash
  sudo apt install libfuse2
  ```
- On first run, if no Discogs token is configured the app opens a Setup screen to guide you through token setup.

### Option D: Tauri `.deb` installer (alternate desktop build)

If you want the Tauri desktop package instead of the GTK build, download:

- [discogs-spinner-tauri_0.2.2_amd64.deb](https://github.com/edonahue/Discogs_Spinner/releases/download/v0.2.2/discogs-spinner-tauri_0.2.2_amd64.deb)
- Checksums: [CHECKSUMS-INSTALLERS.txt](https://github.com/edonahue/Discogs_Spinner/releases/download/v0.2.2/CHECKSUMS-INSTALLERS.txt)
- Fallback release page: [GitHub Releases](https://github.com/edonahue/Discogs_Spinner/releases/latest)

Then install it:

```bash
sudo apt install ./discogs-spinner-tauri_0.2.2_amd64.deb
```

---

## 3) First launch and setup

On first launch, the app should open directly into setup if no token is configured.

- Paste your Discogs personal access token
- Save it
- Start your first collection sync
- Confirm the collection and wantlist views load without errors

Recommended path:

- start with the Snap Store if you want the simplest Linux desktop install
- use the GTK `.deb` if you prefer a direct Debian/Ubuntu package
- use the AppImage if you want a portable no-install path
- use the Tauri `.deb` only if you specifically want the alternate Tauri desktop build

Equivalent CLI flow:

```bash
export DISCOGS_TOKEN="your_discogs_personal_token"
dplayer setup
dplayer sync
dplayer status
dplayer list --limit 10
```

## 4) Optional Spotify onboarding

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

## 5) Source install (advanced)

If you prefer a repo checkout instead of release artifacts:

```bash
sudo apt update
sudo apt install -y \
  python3 python3-venv python3-pip python3-setuptools \
  libsecret-1-0 build-essential python3-dev \
  python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 \
  libadwaita-1-0 gir1.2-gdkpixbuf-2.0 xvfb
git clone https://github.com/edonahue/Discogs_Spinner.git
cd Discogs_Spinner
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .
pip install -e ".[spotify]"
```

## Done? Verify it works

```bash
dplayer status
dplayer spin
```

If `dplayer status` shows your collection count and last sync date, you're all set.

For a clean-machine installer checklist, use [Debian Installer FTUX Validation](validation/debian_installer_ftux.md).

## 6) Troubleshooting

- Run `dplayer setup` for onboarding hints.
- If playback fails, confirm a Spotify device is active and selected.
- Use issue templates for install/auth/playback reports.
