# discogs_player

CLI-first Discogs collection sync tool designed for SSH use on Pop!_OS/Linux.

## System packages (Pop!_OS)

```bash
sudo apt update
sudo apt install -y \
  python3 python3-venv python3-pip python3-setuptools \
  libsecret-1-0 build-essential python3-dev
```

GUI/headless smoke-test packages:

```bash
sudo apt update
sudo apt install -y \
  python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 \
  libadwaita-1-0 gir1.2-gdkpixbuf-2.0 xvfb
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

dplayer match 1393315
dplayer match --unmatched --limit 20
dplayer match override 1393315 spotify:album:abc123
dplayer match 1393315 --json

dplayer play <discogs_release_id>
dplayer play --last-spin
dplayer play --last-spin --auto-match
dplayer play --last-spin --open
dplayer play --last-spin --json

dplayer config show
dplayer config set spotify_client_id abc123
dplayer config unset spotify_client_id
```

Equivalent module invocation:

```bash
python -m discogs_player.main status --json
```

GUI smoke test (headless with Xvfb):

```bash
# Ensure releases exist first:
dplayer sync --no-images

# Run GUI load/render smoke test and exit:
xvfb-run -a python -m discogs_player.ui_main --smoke-test --limit 12
```

GUI match/play flow (new):

```text
1) Use GUI filters (q, year range, genres/styles, unmatched, limit) then Refresh
2) Optional: use Spin section (set seed if desired) and click "Spin"
3) Optional: click "Play Last Spin" to replay most recent spin result
4) Select a release card in the cover grid
5) Click "Auto Match" to run Discogs->Spotify matching (candidate + confidence shown)
6) Optional: paste a Spotify album id/URL and click "Save Override"
7) In "Spotify Device", click "Refresh Devices", then "Set Default" or "Auto Select"
8) Click "Play" to start playback (uses fallback URL messaging in headless-safe scenarios)
```

## Notes

- `sync` soft-deactivates releases missing from Discogs pull (safeguarded when an empty API result is returned unless `--full` is used).
- `--no-images` is accepted for forward compatibility (image caching is not implemented yet).
- GUI scaffold now includes release-grid rendering + cover prefetch/cache for headless smoke testing.
- `play --open` keeps SSH/headless flow safe by printing Spotify URLs instead of requiring GUI launch support.
- Missing dependency errors are handled with actionable install commands instead of tracebacks.
