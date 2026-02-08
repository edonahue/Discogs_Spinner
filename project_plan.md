# discogs_player (Pop!_OS / Linux) — Codex Project Spec (CLI-first + future expansion)

## One-liner
A local Pop!_OS app that syncs my Discogs record collection into a local cache, provides a **CLI “lite” mode** usable over SSH (Termius on iPhone) to browse/filter/spin/play via Spotify, and later adds a desktop UI (GTK4/libadwaita). Designed to expand into broader Discogs collection features (market value, wantlist, etc.).

---

## Project naming
- Project name (repo/package): **discogs_player**
- CLI command: **`dplayer`**
- Python package: **`discogs_player`**
- App display name (UI): **Discogs Player**

---

## Key constraint: SSH-first development
I will frequently build/test via SSH without a monitor. Therefore:
- **All core functionality must be verifiable via CLI**.
- Desktop UI is a thin client over the same core library.
- CLI must provide clear output + optional JSON for scripting.

---

## Goals

### Primary goals (MVP)
1. **Sync Discogs collection** into SQLite + optional image cache.
2. **CLI Lite** (over SSH):
   - `sync`, `status`, `list`, `spin`, `play`, `devices`, `match`, `config`
   - JSON output option for list/spin/status/devices/match
3. **Spotify playback** (Premium):
   - OAuth once
   - Select & persist default device (prefer this desktop / X600)
   - Start album playback on that device
4. **Desktop UI** (GTK4/libadwaita, later):
   - Cover grid + filters + details + spin animation + play
   - Uses the same core library (no duplicated business logic)

### Stretch goals (designed-in, not required for MVP)
These should be hinted in the design (data model + service structure) but not fully implemented initially:
- **Collection market value** (min/median/max per release + total collection value)
- **Wantlist/wishlist** browsing + notifications
- **Seller/marketplace helpers** (links, price history snapshots)
- **Collection analytics** (by year/genre/label, acquisition timeline)
- **Export** (CSV/JSON), **backup**, and **multi-device sync** of the local cache

---

## Non-goals (for now)
- Multi-user support
- Streaming audio directly (Spotify control only)
- Building a full Discogs marketplace client (beyond stretch goal helpers)

---

## Target platform
- Pop!_OS (Linux)
- Python 3
- UI later: GTK4 + libadwaita (PyGObject)
- CLI: Typer + Rich

---

## Architecture (layered, extensible)

### Core (headless library)
- Discogs API client (collection now; later: wantlist, marketplace, prices)
- Spotify API client + OAuth token manager
- SQLite data layer + migrations
- Matching engine (Discogs release → Spotify album)
- Use-cases orchestration services

### Interfaces
- CLI (`dplayer ...`) calls use-cases
- UI calls the same use-cases

Design rule: **No API calls in UI or CLI modules** — only in `services/` and use-cases.

---

## User stories (CLI-centric)
1. Over SSH, I run `dplayer sync` and see progress + a summary.
2. I run `dplayer status` to confirm counts, last sync, mapping state, device state.
3. I run `dplayer list --year 1970:1979 --style Jazz --limit 20`.
4. I run `dplayer spin --genre Rock --year 1990:1999` and it picks an album and remembers “last spin.”
5. I run `dplayer devices` and set default to my desktop Spotify device.
6. I run `dplayer play --last-spin` and it starts playing on my desktop Spotify.

---

## Functional requirements

### 1) Discogs sync (collection ingestion)
- MVP auth: Discogs personal access token.
- Fetch my collection releases (paginated).
- Store minimal release fields in SQLite (see schema).
- Incremental sync: update existing, soft-delete missing.
- CLI progress:
  - `--verbose` shows page-by-page counts
  - default output is concise

### 2) Local data store + caching
- SQLite: `~/.local/share/discogs_player/app.db`
- Cover cache (optional): `~/.cache/discogs_player/covers/`
- CLI should function without images (images are for UI later).

### 3) Spotify playback
- Spotify OAuth (local callback server).
- Required scopes:
  - `user-read-playback-state`
  - `user-modify-playback-state`
  - `user-read-currently-playing` (optional)
- Device management:
  - `dplayer devices` lists devices
  - `dplayer device set <device_id>` persists default
  - `dplayer device auto` chooses a likely desktop computer device
- Playback:
  - `dplayer play <discogs_release_id>` plays on default device
  - `dplayer play --last-spin`
  - If mapped spotify album missing: suggest `dplayer match ...` or print open-in-spotify URL

### 4) Matching (Discogs → Spotify)
- Store mapping in `spotify_mapping` table.
- CLI:
  - `dplayer match <release_id>`
  - `dplayer match --unmatched --limit N`
  - `dplayer match override <release_id> <spotify_album_id>`
- Confidence scoring with `rapidfuzz`.
- Must be headless, return structured results for CLI.

### 5) Spin/random selection
- `dplayer spin [filters...]` selects from filtered set and stores last_spin_release_id.
- Optional deterministic testing: `--seed <int>`.

### 6) Settings and secrets
- CLI config:
  - `dplayer config show`
  - `dplayer config set <key> <value>`
  - `dplayer config unset <key>`
- Prefer `keyring` for tokens; fallback to config file.

---

## CLI specification

### Command: `dplayer status`
Outputs:
- release_count_total
- release_count_active
- mapped_count
- unmatched_count
- last_sync_time
- default_spotify_device (id + cached name if available)
- last_spin_release_id
- (future-friendly) placeholders:
  - market_value_last_updated (null for MVP)
  - wantlist_count (null for MVP)

### Command: `dplayer sync`
Options:
- `--full`
- `--no-images`
- `--verbose`

### Command: `dplayer list`
Options:
- `--limit N` (default 25)
- Filters:
  - `--q "text"`
  - `--genre "Rock"` (repeatable)
  - `--style "Jazz"` (repeatable)
  - `--year 1990:1999`
  - `--unmatched`
- Output:
  - pretty table (default)
  - `--json`

### Command: `dplayer spin`
Same filters as list +:
- `--seed <int>`
- Output includes chosen album + release_id and stores last spin.

### Command: `dplayer devices`
Lists Spotify devices (id, name, type, active, restricted). `--json` optional.

### Command: `dplayer device set <device_id>`
Persists default device id.

### Command: `dplayer play <discogs_release_id>`
Also:
- `dplayer play --last-spin`
Options:
- `--auto-match` (attempt matching if missing)
- `--open` (print/open Spotify URL as fallback)

### Command: `dplayer match`
- `dplayer match <release_id>`
- `dplayer match --unmatched --limit N`
- `dplayer match override <release_id> <spotify_album_id>`

### Command: `dplayer config`
- show/set/unset

Exit codes:
- 0 success
- 2 invalid args
- 3 auth missing
- 4 network/api failure
- 5 playback failure

---

## Data model (SQLite) — MVP + extensibility hooks

### Tables (MVP)
**releases**
- discogs_release_id INTEGER PRIMARY KEY
- artist TEXT
- title TEXT
- year INTEGER
- genres TEXT (JSON)
- styles TEXT (JSON)
- thumb_url TEXT
- cover_url TEXT
- added_at TEXT
- last_synced_at TEXT
- is_active INTEGER

**tracks** (optional)
- id INTEGER PRIMARY KEY AUTOINCREMENT
- discogs_release_id INTEGER
- position TEXT
- title TEXT
- duration TEXT

**spotify_mapping**
- discogs_release_id INTEGER PRIMARY KEY
- spotify_album_id TEXT
- confidence REAL
- last_checked_at TEXT
- is_override INTEGER

**app_settings**
- key TEXT PRIMARY KEY
- value TEXT

### Tables (planned later — do NOT implement for MVP unless easy)
**market_prices**
- discogs_release_id INTEGER PRIMARY KEY
- lowest REAL
- median REAL
- highest REAL
- currency TEXT
- last_updated_at TEXT

**wantlist**
- discogs_release_id INTEGER PRIMARY KEY
- added_at TEXT
- notes TEXT

(These are placeholders to keep the design open for stretch goals.)

---

## Matching algorithm (summary)
- Normalize artist/title strings.
- Spotify search using:
  - `album:{title} artist:{artist}`
  - fallback `{artist} {title}`
- Score top N candidates with `rapidfuzz` + year proximity (+ track count proximity if known).
- Accept if confidence >= threshold; otherwise mark unmatched.

---

## Technology choices

### Python deps (suggested)
- typer
- rich
- httpx
- rapidfuzz
- pillow (optional)
- keyring
- python-dotenv
- pydantic (optional)

UI deps (later; system packages):
- PyGObject GTK4 + libadwaita

---

## Software to install (Pop!_OS)

### Core (CLI/headless)
```bash
sudo apt update
sudo apt install -y \
  python3 python3-venv python3-pip \
  libsecret-1-0
