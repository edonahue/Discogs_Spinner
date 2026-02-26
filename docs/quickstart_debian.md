# Quickstart (Debian Linux)

This guide targets first-time users installing `discogs_player` on Debian/Ubuntu.

## 1) Prerequisites

- Debian 12+ (or Ubuntu equivalent)
- Discogs account + personal token
- Optional: Spotify account (for playback/matching features)

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
git clone https://github.com/<your-user>/discogs_player.git
cd discogs_player
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

## 5) Optional Spotify onboarding

```bash
dplayer auth spotify-doctor
dplayer auth spotify --open-browser --listen-host 127.0.0.1 --listen-port 8765
dplayer devices --json
```

Safe first play fallback:

```bash
dplayer play --last-spin --open
```

## 6) Troubleshooting

- Run `dplayer setup` for onboarding hints.
- If playback fails, confirm a Spotify device is active and selected.
- Use issue templates for install/auth/playback reports.
