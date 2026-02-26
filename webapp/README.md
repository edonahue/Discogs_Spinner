# discogs_player Web App

React + TypeScript frontend scaffold for the local `dplayer-api` service.

## Current scope

- Reads status data from the API and renders a lightweight dashboard.
- Uses `GET /api/v1/status` as the primary integration contract.
- Intended to remain API-first so it can be wrapped by desktop packaging later.

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
