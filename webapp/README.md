# Discogs Spinner Web App

React + TypeScript multi-page frontend for the local `dplayer-api` service.

API-first design — all data flows through the FastAPI backend so the webapp can be
wrapped by Tauri for desktop distribution or served directly from any browser.
Does not stream audio; playback is delegated to external services.

## Pages

| Route | Page |
|-------|------|
| `/` | Home — status dashboard, collection counts, last sync, sync trigger buttons |
| `/collection` | Collection — searchable, filterable, sortable release list with genre tags and optional market value |
| `/wantlist` | Wantlist — searchable, filterable, sortable wantlist with genre tags and optional market value |
| `/value` | Value — top releases by market price, Hidden Gems, refresh queue, and collection handoffs |
| `/health` | Health — collection quality score with gap buckets |
| `/recent` | Recently Added — recent collection changes with focused collection handoffs |
| `/analytics` | Analytics — collection trends by year, genre, style, and artist |
| `/setup` | Setup — first-run token configuration; redirected to if unconfigured |

## Features

### Collection & Wantlist
- **Search** — debounced text search across artist/title
- **Filter bar** — year input, genre input, "Unmatched only" toggle (Collection only), "Show value" toggle
- **Sort** — client-side: Artist A→Z/Z→A, Title A→Z, Year newest/oldest, Value high→low (when value shown)
- **Genre/style pills** — up to 3 tags shown per release row
- **Market value column** — median price in green when "Show value" is checked; enables value sort
- **Load more** — pagination in increments of 25
- **Focused detail** — `?focus=<release_id>` keeps a release detail panel visible after internal handoffs
- **Collection summary** — LP count, 45 count, median value, and most-recently-added context on Collection

### Home
- Collection stats (total, active, mapped, unmatched, wantlist count, last sync time)
- **Sync Collection** and **Sync Wantlist** buttons with syncing/success/error feedback

### Value dashboard
- Top 10 releases by median market price
- Hidden Gems ranked by value and current scarcity
- Refresh queue candidates for missing, unpriced, or stale value data
- Last-updated timestamp from the API
- **Refresh Values** button — triggers a background value refresh, reloads on completion
- **View in Collection** handoffs — every actionable release link opens Collection with the release focused

### Recent, Health, and Analytics
- Recent page shows newest collection additions and preserves collection handoff context
- Health page surfaces mapping, value, and staleness gaps as a score
- Analytics page shows collection distribution by release year, acquisition year, genre, style, and artist

## API surface

| Method | Endpoint | Params | Used by |
|--------|----------|--------|---------|
| `GET` | `/api/v1/status` | — | Home |
| `POST` | `/api/v1/sync/collection` | — | Home |
| `POST` | `/api/v1/sync/wantlist` | — | Home |
| `GET` | `/api/v1/releases` | `q`, `year`, `genres[]`, `styles[]`, `unmatched`, `with_value`, `limit` | Collection |
| `GET` | `/api/v1/releases/summary` | — | Collection |
| `GET` | `/api/v1/releases/recent` | `days`, `limit` | Recent |
| `GET` | `/api/v1/releases/{id}` | `with_value` | Focused Collection detail |
| `GET` | `/api/v1/releases/{id}/tracklist` | — | Collection tracklist modal |
| `GET` | `/api/v1/wantlist` | `q`, `year`, `genres[]`, `styles[]`, `with_value`, `limit` | Wantlist |
| `GET` | `/api/v1/wantlist/{id}` | `with_value` | Focused Wantlist detail |
| `GET` | `/api/v1/value/dashboard` | `top_limit` | Value |
| `GET` | `/api/v1/value/queue` | `limit`, `stale_days`, `missing_only` | Value |
| `GET` | `/api/v1/value/gems` | `min_median`, `limit` | Value |
| `GET` | `/api/v1/value/health` | — | Health |
| `POST` | `/api/v1/value/refresh` | `from_missing`, `limit`, `stale_days` | Value |
| `GET` | `/api/v1/analytics` | `top_limit` | Analytics |
| `GET` | `/api/v1/setup` | — | Setup |
| `POST` | `/api/v1/setup` | — | Setup |

## Prerequisites

- Node.js 20+
- Repo-level Python env with web extras installed (`pip install -e ".[web]"`)

## Local development

From repository root:

```bash
# terminal 1: start local API
dplayer-api

# terminal 2: run web app
npm --prefix webapp install
npm --prefix webapp run dev
```

Vite dev server default URL is `http://127.0.0.1:5173`.

## Production build

```bash
npm --prefix webapp run build
```

Output is written to `webapp/dist/`.

## Environment

- `VITE_API_BASE_URL` (optional): override API base URL.
- Default value: `http://127.0.0.1:8768/api/v1`.
