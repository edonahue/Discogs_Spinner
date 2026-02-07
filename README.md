# discogs_player

CLI-first Discogs collection sync tool designed for SSH use on Pop!_OS/Linux.

## System packages (Pop!_OS)

```bash
sudo apt update
sudo apt install -y \
  python3 python3-venv python3-pip \
  libsecret-1-0
```

If a Python package build fails in your environment, also install:

```bash
sudo apt install -y build-essential python3-dev
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
```

Equivalent module invocation:

```bash
python -m discogs_player.main status --json
```

## Notes

- `sync` currently soft-deactivates releases missing from the latest Discogs pull.
- `--no-images` is accepted for forward compatibility (image caching is not implemented yet).
- Missing dependency errors are handled with actionable install commands instead of tracebacks.
