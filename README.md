# Discogs Spinner

Discogs-first collection sync and external-playback helper with a CLI core plus
optional Spotify, API, web, and desktop-distribution layers.

Important: this app does not stream audio inside its own UI. It opens and
controls playback in external apps/services (for example Spotify).

Repository name: `Discogs_Spinner`  
Internal Python package/CLI names currently remain `discogs_player` / `dplayer`.

## Product State And Roadmap

Current canonical product state:

- `PRODUCT_STATE.md` (goals, current capabilities, risks, dated roadmap)
- `docs/STATUS_CHECKPOINT_2026-02-26.md` (current execution checkpoint + publish blocker/next actions)
- `docs/CROSS_PLATFORM_IMPLEMENTATION_ROADMAP.md` (API/web/desktop execution order)
- `docs/STRATEGIC_EXPANSION_NOTES_2026-02-26.md` (ambitious long-term + medium-term + short-term release/monetization intent)
- `docs/RELEASE_CHECKLIST_WINDOWS_DEBIAN_MACOS.md` (staged release gate: Windows -> Debian -> macOS)
- `docs/RELEASE_CHECKLIST_FIRST_PASS_2026-02-26.md` (first checklist/runbook execution evidence)
- `docs/RC_RELEASE_RUNBOOK.md` (tag-and-publish release-candidate procedure)
- `docs/RELEASE_NOTES_TEMPLATE.md` (standard release notes format)

Current stabilization execution backlog:

- `STABILIZATION_BACKLOG_2026Q1.md` (Phase 2 kickoff: bug/perf/usability only)

Latest validation evidence:

- `docs/TESTING_PERFORMED_2026-02-26.md`
- `docs/TESTING_PERFORMED_2026-02-23.md` (previous baseline)

Historical snapshots (not canonical current state):

- `PROJECT_SNAPSHOT.md`
- `PROJECT_ASSESSMENT.md`
- `DOCUMENTATION_SUMMARY.md`

## Legal And Compliance Baseline

- `LICENSE`
- `PRIVACY.md`
- `TERMS.md`
- `TRADEMARKS.md`
- `COMPLIANCE.md`

## OS Quickstarts

- `docs/quickstart_windows.md`
- `docs/quickstart_debian.md`
- `docs/quickstart_macos.md`

## Component READMEs

- `webapp/README.md`
- `desktop_shell/README.md`

## Before First Public Push

Run this minimum release hygiene gate from repo root:

```bash
git status -sb
bash ./scripts/prepublish_hygiene_check.sh
venv/bin/ruff check .
venv/bin/python -m mypy src/discogs_player --show-error-codes --hide-error-context
venv/bin/python -m pytest -q
npm --prefix webapp run build
```

Notes:

- Keep only placeholder values in `.env.example`.
- Do not commit real `.env` files, tokens, local databases, logs, or exports.

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
# Core profile (Discogs sync/browse only)
pip install -e .

# Optional Spotify addon profile
pip install -e ".[spotify]"

# Optional API/Web profile
pip install -e ".[web]"
```

`DISCOGS_TOKEN` is read from your environment first (recommended):

```bash
export DISCOGS_TOKEN="your_discogs_personal_token"
```

Spotify playback (optional addon) supports either a direct access token or refresh credentials:

```bash
# Option 1: direct access token
export SPOTIFY_ACCESS_TOKEN="..."

# Option 2: auto-refresh
export SPOTIFY_CLIENT_ID="..."
export SPOTIFY_SECRET="..."
# Legacy alias still accepted:
# export SPOTIFY_CLIENT_SECRET="..."
export SPOTIFY_REFRESH_TOKEN="..."
```

You can also keep values in `.env` (see `.env.example`), but keep `.env` local-only
and out of version control.

## Core vs Plus profiles

- `discogs_player-core`: install with `pip install .`
- `discogs_player-plus`: install with `pip install ".[spotify]"`
- `discogs_player-web`: install with `pip install ".[web]"`

Build OS-tagged artifact bundles for both:

```bash
./scripts/build_artifacts.sh all
```

If you need offline/local build isolation disabled:

```bash
PIP_NO_BUILD_ISOLATION=1 ./scripts/build_artifacts.sh all
```

If you also need to skip dependency wheel resolution:

```bash
PIP_NO_BUILD_ISOLATION=1 PIP_WHEEL_NO_DEPS=1 ./scripts/build_artifacts.sh all
```

Artifacts are written under `dist/artifacts/<os>-<arch>/` as:

- `discogs_player-core-<os>-<arch>.tar.gz`
- `discogs_player-plus-<os>-<arch>.tar.gz`

CI workflow for the same split is defined in:

- `.github/workflows/core_plus_ci.yml`
- Separate test jobs:
  - core profile: `pip install .`
  - plus profile: `pip install ".[spotify]"`
- Artifact build/upload matrix: Linux, macOS, Windows

Latest local verification reports:

- `docs/TESTING_PERFORMED_2026-02-26.md`
- `docs/TESTING_PERFORMED_2026-02-23.md` (previous baseline)

## Spotify Live Smoke Test

Run a repeatable live smoke flow for Spotify addon behavior:

```bash
./scripts/spotify_live_smoke.sh
```

If Spotify is not configured yet, run interactive auth inside the smoke flow:

```bash
./scripts/spotify_live_smoke.sh --auth
```

Optional explicit release id for the play/open check:

```bash
SPOTIFY_SMOKE_RELEASE_ID=249504 ./scripts/spotify_live_smoke.sh
```

## API + Web Scaffold

Local API entrypoint:

```bash
dplayer-api
```

This starts the API server on `http://127.0.0.1:8768`.

Run API + web app locally:

```bash
# terminal 1
dplayer-api

# terminal 2
npm --prefix webapp run dev
```

Primary endpoints:

- `GET /healthz`
- `GET /api/v1/status`
- `GET /api/v1/capabilities`
- `GET /api/v1/releases`
- `GET /api/v1/wantlist`
- `POST /api/v1/sync/collection`
- `POST /api/v1/sync/wantlist`
- `POST /api/v1/play/{discogs_release_id}`
- `POST /api/v1/match/{discogs_release_id}`
- `POST /api/v1/match/audit`
- `POST /api/v1/match/review/{apply|reject}`
- `GET /api/v1/value/status`
- `GET /api/v1/value/dashboard`
- `POST /api/v1/value/refresh`

Web-client scaffold docs live in:

- `webapp/README.md`

Desktop-shell scaffold docs live in:

- `desktop_shell/README.md`

## Slow External Spotify Mapping (Hours-Scale)

For large catalog mapping runs, prefer the external worker script over interactive
CLI usage. It runs resumable `match audit` batches with explicit delay/backoff:

```bash
./scripts/spotify_catalog_map_slow.sh \
  --batch-limit 1 \
  --request-delay-seconds 0.5 \
  --max-retries 10 \
  --backoff-seconds 4 \
  --loop-sleep-seconds 30 \
  --heartbeat-seconds 10 \
  --audit-timeout-seconds 1800 \
  --log-path ~/.local/state/discogs_player/spotify_catalog_map_slow.log
```

By default, the worker maps unmatched **collection** releases (`--scope collection`).
To map only unmatched wantlist items without mixing batches with your collection run:

```bash
./scripts/spotify_catalog_map_slow.sh \
  --scope wantlist \
  --batch-limit 1 \
  --request-delay-seconds 1.5 \
  --max-retries 2 \
  --backoff-seconds 3 \
  --api-max-retries 1 \
  --loop-sleep-seconds 90 \
  --compact-audit-output
```

You can also run `--scope both` for a combined de-duplicated queue. Scope-specific
default report files are used to avoid resume-state mixing:

- collection: `spotify_match_audit_slow.json`
- wantlist: `spotify_match_audit_slow_wantlist.json`
- both: `spotify_match_audit_slow_combined.json`

The worker enables compact audit JSON output by default to reduce stdout/memory churn
on multi-hour runs. Use `--full-audit-output` only when you need full payloads.
It now also enables in-batch per-release progress rows via `match audit --progress-log`
so you can tail retry/start/complete events before each batch returns.
Safe auto-apply is enabled by default in worker mode (`match audit --apply-safe`);
disable with `--no-apply-safe-matches` if you want audit-only runs.
Worker now uses a lock file so only one mapper instance runs at a time.
The worker also sets a conservative Spotify API retry profile by default to avoid
multi-minute stalls on one release:

- `DP_SPOTIFY_API_MAX_RETRIES=1`
- `DP_SPOTIFY_API_BACKOFF_SECONDS=1.0`
- `DP_SPOTIFY_API_MAX_SLEEP_SECONDS=15.0`
- `DP_SPOTIFY_API_JITTER_SECONDS=0.1`

Optional bootstrap import from external mapping tools before the worker loop:

```bash
./scripts/spotify_catalog_map_slow.sh \
  --bootstrap-input ~/backups/discogs_to_spotify_export.json \
  --bootstrap-format discogs-to-spotify \
  --bootstrap-conflict merge
```

`match audit` backoff is exponential. For one release, retry wait ceiling is:

`backoff_seconds * (2^max_retries - 1)`

Example: `--max-retries 10 --backoff-seconds 4` means up to `4092s` (~68 minutes)
before one release attempt is considered exhausted.

Tail progress (including per-release batch rows) while the worker runs detached:

```bash
tail -f ~/.local/state/discogs_player/spotify_catalog_map_slow.log
```

Quick mapping snapshot from SQLite:

```bash
./scripts/spotify_mapping_report.sh
./scripts/spotify_mapping_report.sh --limit 50
```

## Data locations (XDG)

- SQLite DB: `~/.local/share/discogs_player/app.db`
- Config/settings: `~/.config/discogs_player/`
- Cache: `~/.cache/discogs_player/`

## CLI usage (SSH-friendly)

```bash
dplayer status
dplayer status --json
dplayer setup
dplayer setup --json
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
dplayer art status
dplayer art status --json
dplayer art refresh --scope collection --dry-run --json
dplayer art refresh --scope collection --target-size 1400 --enable
dplayer art refresh --scope both --limit 100 --workers 12 --json
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
dplayer bootstrap import --input ~/backups/discofy_transfer_status.json --format discofy --dry-run
dplayer bootstrap import --input ~/backups/discogs_spotify_map.csv --format direct --dry-run
dplayer bootstrap import --input ~/backups/discogs_spotify_map.csv --format direct --conflict-mode merge
dplayer bootstrap import --input ~/backups/discogs_to_spotify_export.json --format discogs-to-spotify --dry-run
python scripts/convert_discofy_bootstrap.py --input ~/backups/discofy_transfer_status.json --output ~/backups/discogs_spotify_bootstrap.json --format discofy
python scripts/convert_discofy_bootstrap.py --input ~/backups/discogs_to_spotify_export.json --output ~/backups/discogs_spotify_bootstrap.json --format discogs-to-spotify
python scripts/convert_discofy_bootstrap.py --input ~/backups/discogs_spotify_bootstrap.json --output ~/backups/discogs_spotify_bootstrap.csv --format direct --output-format csv
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
dplayer auth spotify-doctor
dplayer auth spotify-doctor --json
dplayer auth spotify --open-browser
dplayer auth spotify --listen-port 8765
dplayer auth spotify --manual
dplayer auth spotify --manual --callback-url "http://127.0.0.1:8765/callback?code=...&state=..."
dplayer auth spotify --manual --code "<spotify_authorization_code>"

dplayer match 1393315
dplayer match --unmatched --limit 20
dplayer match --unmatched --limit 20 --auto-apply-threshold 0.90
dplayer match override 1393315 spotify:album:abc123
dplayer match 1393315 --json
dplayer match audit --resume --report ~/.local/share/discogs_player/reports/spotify_match_audit_latest.json
dplayer match audit --apply-safe --resume --report ~/.local/share/discogs_player/reports/spotify_match_audit_latest.json
dplayer match audit --limit 100 --request-delay-seconds 0.15 --max-retries 5 --backoff-seconds 2.0 --retry-errors --compact --json

dplayer review list --report ~/.local/share/discogs_player/reports/spotify_match_audit_latest.json
dplayer review apply --all
dplayer review reject --all
dplayer review retry-errors --report ~/.local/share/discogs_player/reports/spotify_match_audit_latest.json

dplayer play <discogs_release_id>
dplayer play --last-spin
dplayer play --last-spin --auto-match
dplayer play --last-spin --open
dplayer play --last-spin --json

dplayer open <discogs_release_id>
dplayer open <discogs_release_id> --copy

dplayer recent
dplayer recent --days 30 --limit 20
dplayer recent --json

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
- It also runs `dplayer tracks refresh` once per UTC week (default `--stale-days 7 --limit 10000`)

Tracklist weekly refresh controls:

- `DP_SYNC_TRACKLIST_WEEKLY_ENABLED` (`1` by default; set `0` to disable)
- `DP_SYNC_TRACKLIST_STALE_DAYS` (`7` by default)
- `DP_SYNC_TRACKLIST_LIMIT` (`10000` by default)
- `DP_SYNC_TRACKLIST_WEEK_MARKER_PATH` (defaults to `~/.local/state/discogs_player/tracklist_refresh_week.txt`)

## Notes

- `sync` soft-deactivates releases missing from Discogs pull (safeguarded when an empty API result is returned unless `--full` is used).
- `--no-images` is accepted for forward compatibility (sync does not currently prefetch image binaries).
- `export`/`import` snapshots now include cached market price fields (`market_lowest/median/highest`, currency, timestamp).
- `bootstrap import` adds mapping-only ingest for external tooling:
  - `--format discofy` reads nested Discofy-style transfer JSON and extracts release->Spotify album candidates.
  - `--format discogs-to-spotify` is an alias to the same nested parser for Discogs-to-Spotify style exports.
  - `--format direct` is the fallback for hand-curated CSV/JSON with `discogs_release_id` + `spotify_album_id` (or Spotify album URI/URL).
  - `--format auto` tries Discofy parsing first, then direct parsing.
- `scripts/convert_discofy_bootstrap.py` converts Discofy/direct inputs into canonical direct bootstrap files for repeatable imports.
- `scripts/spotify_catalog_map_slow.sh` is the recommended long-running worker for large Spotify mapping jobs (resumable audit batches + throttled pacing).
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
- `tracks show <release_id>` shows cached tracklist rows for one release, and `--refresh` pulls latest rows from Discogs first.
- `tracks refresh` fills/updates the tracklist cache for active releases (missing, stale-window, or explicit `--release-id` set).
- `art status` reports whether opt-in high-res art is enabled and which target size is configured.
- `art refresh` pre-warms cover cache for collection/wantlist scopes and attempts upgraded Discogs sizes when safe; signed Discogs proxy URLs are warmed at original URL/quality to avoid `403` mismatches.
- GUI browse view now offers an iPod-inspired dark UI with both text-menu and cover-carousel modes.
- GUI filters now include shared sorting controls (including Year and Genre) used by both browse modes.
- `play --open` keeps SSH/headless flow safe by printing Spotify URLs instead of requiring GUI launch support.
- `auth spotify` runs a local callback OAuth flow and stores secrets in keyring when available (falls back to app settings). If callback binding/timeout fails, CLI prompts for manual callback URL/code entry; manual mode is also available via `--manual`.
- `auth spotify-doctor` reports auth readiness, expected redirect URI, credential/token source availability, and optional device probe results.
- `setup` provides first-time onboarding state + next-step commands across Discogs core and optional Spotify addon setup.
- `diagnostics` emits a redacted support bundle for issue reports; use `dplayer diagnostics --json`.
- Provider registry now lists planned providers separately from enabled providers; YouTube Music scaffold is listed but disabled by default (`DP_ENABLE_EXPERIMENTAL_YOUTUBE_MUSIC=1` to expose experimental wiring).
- Architecture guardrail: core/use-case modules must not import Spotify modules directly; use `discogs_player.capabilities.get_player_backend()` and `PlayerBackend` instead.
- Spotify integration code lives under `src/discogs_player/integrations/spotify/`; keep optional addon behavior capability-aware in CLI/UI (`Enable Spotify (optional)` vs `Connect Spotify`).
- Keep external bootstrap parsers integration-agnostic and in core/use-case code (`use_cases/bootstrap_import.py`), with direct-schema fallback retained for long-term compatibility.
- Matching safety guardrail:
  - automated apply paths (`match --unmatched`, `play --auto-match`, `match audit --apply-safe`) only persist mappings at/above confidence `0.90`.
  - candidates in `0.72-0.89` are queued for review in audit/report output and not auto-written.
  - use `dplayer review apply/reject` for first-class manual review decisions (single IDs or `--all`).
  - use `dplayer review retry-errors` (or `match audit --resume --retry-errors`) to reprocess prior `429`/error entries.
  - use `--scope collection|wantlist|both` to control matching population; resume now enforces report scope consistency to prevent collection/wantlist cross-mixing.
  - keep rate-limit handling in place for collection audits (`429` retry/backoff + resumable report export).
  - Spotify API client also retries `429` responses with bounded backoff (`Retry-After` respected when present); tune with:
    - `DP_SPOTIFY_API_MAX_RETRIES`
    - `DP_SPOTIFY_API_BACKOFF_SECONDS`
    - `DP_SPOTIFY_API_MAX_SLEEP_SECONDS`
    - `DP_SPOTIFY_API_JITTER_SECONDS`
    - `DP_SPOTIFY_API_RETRY_AFTER_CAP_SECONDS`
  - Runtime guardrail: extremely large Spotify `Retry-After` headers are capped to keep interactive CLI/UI actions responsive (default cap `15s`, with fallback to `DP_SPOTIFY_API_MAX_SLEEP_SECONDS` when cap is disabled).
  - UI-triggered auto-match/play paths use fail-fast audit retry settings (single-attempt behavior) so one rate-limited release does not block the desktop app for minutes.
- Missing dependency errors are handled with actionable install commands instead of tracebacks.
