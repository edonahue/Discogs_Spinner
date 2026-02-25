# Project Snapshot: `discogs_player`

> Historical snapshot captured on 2026-02-08.
> For current goals/capabilities/roadmap, use `PRODUCT_STATE.md`.

As of **2026-02-08 (UTC)**.

## Completeness Rating

**Overall: 88/100 (feature-complete MVP+, integration-hardening in progress).**

Breakdown:

- Core Discogs sync + local data model: **92/100**
- CLI surface and automation workflows: **90/100**
- GUI usability (browse/spin/device/match/play): **83/100**
- Spotify integration and production polish: **78/100**
- Packaging/scripts/docs/tests: **89/100**

## Current Status

- Branch: `master`
- Latest commit: `a1a7e26` (`spotify oauth and keyring`)
- Working tree: **dirty** with substantial in-progress changes (expanded CLI/use-cases/UI/scripts/tests)
- Automated tests: **151 passed** (`pytest -q`)

Current local data snapshot:

- Collection releases: `181` total / `181` active
- Wantlist releases: `10` total / `10` active
- Market price rows: `179`
- Market snapshots: `0`
- Spotify mapped releases (local DB): `0` (currently ignored per latest workflow)

Recent one-time Discogs-only CSV export:

- File: `exports/discogs_data_refresh_20260208T021524Z.csv`
- Rows: `191` (`181` collection + `10` wantlist)
- Includes Discogs metadata + local market-value fields, excludes Spotify columns

## Architecture (Concise)

Layered architecture with shared use-cases across CLI and GUI:

- `core/`: paths, settings, runtime config
- `data/`: SQLite schema/migrations + repository queries
- `services/`: core API/data services (Discogs client, image cache, sync orchestration)
- `integrations/`: optional addon backends (Spotify + null backend via capabilities)
- `use_cases/`: business operations (`sync`, `list`, `spin`, `match`, `play`, `value`, `wantlist`, import/export, analytics)
- `cli/`: Typer command wiring + Rich rendering
- `ui/`: GTK4/libadwaita desktop interface over the same use-cases (no API calls in widgets)

Primary runtime data flow:

1. Discogs API -> `services/discogs_client.py`
2. Normalized records -> SQLite (`data/db.py`, `data/repo.py`)
3. CLI/GUI read same use-cases from `use_cases/`
4. GUI cover rendering -> local cache paths from `services/image_cache.py`

## Software Used

Python and core libraries:

- Python `>=3.10`
- `typer`, `rich`
- `httpx`
- `rapidfuzz`
- `python-dotenv`
- `keyring`
- SQLite (`app.db` in XDG data path)

Desktop/runtime tooling:

- GTK4 + libadwaita via PyGObject
- Xvfb-based GUI smoke testing
- Cron helper scripts for scheduled sync

Pop!_OS integration:

- Desktop launcher install/uninstall scripts
- XDG-compliant paths for config/data/cache

## Known Gaps / Next Focus

- Commit and slice current large working-tree change-set into coherent PR-sized chunks
- Decide desired Spotify depth for this phase (currently intentionally deprioritized)
- Add/expand GUI behavior tests around resize ergonomics (already improved, still mostly smoke-tested)
- Add periodic market snapshot capture if trend analysis is a priority
