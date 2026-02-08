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
dplayer value status
dplayer value status --json
dplayer value examples --limit 2
dplayer value examples --json
dplayer value snapshot
dplayer value trend --limit 30 --json
dplayer value show 249504
dplayer value show 249504 --refresh --json
dplayer value missing --limit 25 --json
dplayer value missing --stale-days 30 --with-value
dplayer value missing --stale-days 30 --csv ~/backups/value_missing.csv
dplayer value refresh --stale-days 30
dplayer value refresh --from-missing --stale-days 30 --limit 100
dplayer value refresh --release-id 249504 --release-id 1933642 --json
dplayer value refresh --limit 50 --verbose --json
dplayer wantlist sync
dplayer wantlist sync --full --verbose
dplayer wantlist list --limit 25
dplayer wantlist list --with-value --limit 25
dplayer wantlist list --year 1970:1979 --genre Rock --json
dplayer export --output ~/backups/discogs_player_backup.json --format json
dplayer export --output ~/backups/discogs_player_releases.csv --format csv --active-only
dplayer import --input ~/backups/discogs_player_backup.json --conflict-mode merge
dplayer import --input ~/backups/discogs_player_backup.json --conflict-mode replace --dry-run
dplayer import --input ~/backups/discogs_player_backup.json --no-settings --json
dplayer list --limit 25
dplayer list --with-value --limit 25
dplayer list --year 1990:1999 --genre Rock --style Jazz --json
dplayer analytics
dplayer analytics --limit 15
dplayer analytics --json

dplayer spin --genre Rock --year 1990:1999
dplayer spin --seed 42 --json

dplayer devices
dplayer devices --json
dplayer device auto
dplayer device set <device_id>
dplayer auth spotify --open-browser
dplayer auth spotify --listen-port 8765

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
2) Select browse mode: "Text Menu" (iPod list) or "Carousel" (flip album covers with Prev/Next)
3) Use Sort dropdown to order by Artist/Title, Year, or Genre (both modes share this ordering)
4) Optional: use Spin section (set seed if desired) and click "Spin"
5) Optional: click "Play Last Spin" to replay most recent spin result
6) Select a release in the text menu or carousel
7) Click "Auto Match" to run Discogs->Spotify matching (candidate + confidence shown)
8) Optional: paste a Spotify album id/URL and click "Save Override"
9) In "Spotify Device", click "Refresh Devices", then "Set Default" or "Auto Select"
10) Click "Play" to start playback (uses fallback URL messaging in headless-safe scenarios)

Keyboard/scroll controls (iPod-style):

- Up/Down/Left/Right: move to previous/next album in current sorted order
- Enter: toggle Text Menu <-> Carousel while keeping current selection
- Mouse wheel over browse panel: scroll up/down to move through albums
```

## Pop!_OS COSMIC desktop launcher

Install a desktop app entry + icon (searchable in app launcher and pinnable to dock):

```bash
./scripts/install_desktop_app.sh
```

This installs:

- launcher script: `~/.local/bin/discogs-player-gui`
- desktop entry: `~/.local/share/applications/discogs-player.desktop`
- icon: `~/.local/share/icons/hicolor/scalable/apps/discogs-player.svg`

Then:

1) Open the COSMIC app launcher and search for `Discogs Player`
2) Launch it once
3) Right-click the running icon and choose `Pin to Dock`

To remove the desktop integration later:

```bash
./scripts/uninstall_desktop_app.sh
```

If launcher clicks fail silently, check:

- `~/.local/state/discogs_player/gui-launch.log`

## Scheduled sync (cron)

Run sync in the background on a schedule:

```bash
# Install/update schedule (default: minute 17 every 6 hours)
./scripts/setup_sync_schedule.sh install

# Install with explicit cron expression
./scripts/setup_sync_schedule.sh install "17 */6 * * *"

# Show current discogs_player schedule entry
./scripts/setup_sync_schedule.sh show

# Remove the scheduled entry
./scripts/setup_sync_schedule.sh remove
```

The scheduled job executes:

- `scripts/run_scheduled_sync.sh`
- It runs `dplayer sync --no-images` and logs to `~/.local/state/discogs_player/sync.log`

## Notes

- `sync` soft-deactivates releases missing from Discogs pull (safeguarded when an empty API result is returned unless `--full` is used).
- `--no-images` is accepted for forward compatibility (sync does not currently prefetch image binaries).
- `export`/`import` snapshots now include cached market price fields (`market_lowest/median/highest`, currency, timestamp).
- `list` and `wantlist list` support `--with-value` to include cached market fields in JSON/table output.
- `value snapshot` stores point-in-time totals in `market_value_snapshots`; `value trend` reports deltas across recent snapshots.
- `value show <release_id>` returns one release's cached market stats, while `value missing` lists active releases that still need pricing.
- `value status` (table mode) now includes high/low priced examples with explicit `Artist` + `Album` names.
- `value examples` gives those same high/low examples directly (CLI JSON/table and GUI sidebar use the same source data).
- `value show --refresh` pulls fresh price suggestions from Discogs, updates local cache, then returns the updated result.
- `value missing --stale-days N` broadens that list to include stale cached entries needing refresh, and `--with-value` shows cached columns.
- `value missing --csv <path>` writes backlog rows (including `market_need_reason`) for offline review.
- `value refresh --from-missing` refreshes exactly from that backlog selector (missing + unpriced + stale with `--stale-days`).
- `value refresh --release-id ...` lets you target specific active release IDs instead of running a broad stale refresh.
- GUI browse view now offers an iPod-inspired dark UI with both text-menu and cover-carousel modes.
- GUI filters now include shared sorting controls (including Year and Genre) used by both browse modes.
- `play --open` keeps SSH/headless flow safe by printing Spotify URLs instead of requiring GUI launch support.
- `auth spotify` runs a local callback OAuth flow and stores secrets in keyring when available (falls back to app settings).
- Missing dependency errors are handled with actionable install commands instead of tracebacks.
