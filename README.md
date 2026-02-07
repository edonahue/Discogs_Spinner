# discogs_player

CLI-first Discogs collection sync tool designed for SSH use on Pop!_OS/Linux.

## System packages (Pop!_OS)

```bash
sudo apt update
sudo apt install -y \
  python3 python3-venv python3-pip python3-setuptools \
  libsecret-1-0 build-essential python3-dev
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

`DISCOGS_TOKEN` is read from your environment first (recommended):

```bash
export DISCOGS_TOKEN="your_discogs_personal_token"
```

Spotify playback supports either a direct access token or refresh credentials:

```bash
# Option 1: direct access token
export SPOTIFY_ACCESS_TOKEN="..."

# Option 2: auto-refresh
export SPOTIFY_CLIENT_ID="..."
export SPOTIFY_CLIENT_SECRET="..."
export SPOTIFY_REFRESH_TOKEN="..."
```

You can also keep values in `.env` (see `.env.example`).

## Data locations (XDG)

- SQLite DB: `~/.local/share/discogs_player/app.db`
- Config/settings: `~/.config/discogs_player/`
- Cache: `~/.cache/discogs_player/`

## CLI usage (SSH-friendly)

```bash
dplayer status
dplayer status --json
dplayer sync
dplayer sync --verbose
dplayer list --limit 25
dplayer list --year 1990:1999 --genre Rock --style Jazz --json

dplayer spin --genre Rock --year 1990:1999
dplayer spin --seed 42 --json

dplayer devices
dplayer devices --json
dplayer device auto
dplayer device set <device_id>

dplayer play <discogs_release_id>
dplayer play --last-spin
dplayer play --last-spin --json
```

Equivalent module invocation:

```bash
python -m discogs_player.main status --json
```

## Notes

- `sync` soft-deactivates releases missing from Discogs pull (safeguarded when an empty API result is returned unless `--full` is used).
- `--no-images` is accepted for forward compatibility (image caching is not implemented yet).
- Missing dependency errors are handled with actionable install commands instead of tracebacks.
