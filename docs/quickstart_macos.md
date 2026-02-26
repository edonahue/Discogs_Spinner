# Quickstart (macOS)

This guide targets first-time users installing `discogs_player` on macOS.

## 1) Prerequisites

- macOS 13+
- Homebrew installed
- Discogs account + personal token
- Optional: Spotify account (for playback/matching features)

Install base tools:

```bash
brew update
brew install python@3.12 git
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

## 6) Notes

- Keep this as a CLI-first setup path unless a signed macOS app build is provided.
- If browser callback fails, use manual callback options from `dplayer auth spotify --help`.
