# Web App Quickstart

> Works on **Windows, macOS, and Linux** — no GTK or WSL2 required.

The web app consists of two parts running on your local machine:

- **API server** (`dplayer-api`) — Python process that talks to your SQLite database
- **Browser frontend** — React app served by a local dev server (or bundled via Tauri for release builds)

---

## Prerequisites

> **Estimated time:** ~10 minutes

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.10+ | Already required for the CLI |
| Node.js | 20+ | Only needed to run the frontend dev server |

---

## Step 1 — Install

```bash
python3 -m venv .venv

# Linux / macOS
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

pip install -e ".[web]"
```

> **Note:** `pip install -e ".[web]"` installs the `fastapi` and `uvicorn` dependencies that
> `dplayer-api` requires. A plain `pip install -e .` (core profile) will not include these.

---

## Step 2 — Set your Discogs token

```bash
# Linux / macOS
export DISCOGS_TOKEN="your_discogs_personal_access_token"

# Windows (PowerShell)
$env:DISCOGS_TOKEN = "your_discogs_personal_access_token"
```

Need a token? [Get your Discogs personal access token →](token_setup.md)

If the token is not set, the app will redirect you to a setup page automatically (see [First-run FTUX](#first-run-ftux) below).

---

## Step 3 — Start the API server

```bash
dplayer-api
```

You should see:

```
Spinner for Discogs API — http://127.0.0.1:8768  (Ctrl+C to stop)
INFO:     Started server process [...]
INFO:     Uvicorn running on http://127.0.0.1:8768
```

Leave this terminal running. The API must be running for the frontend to work.

---

## Step 4 — Start the frontend dev server

Open a **second terminal** (with the virtualenv active) and run:

```bash
npm --prefix webapp install   # first time only
npm --prefix webapp run dev
```

You should see:

```
  VITE v5.x.x  ready in ...ms

  ➜  Local:   http://localhost:5173/
```

Open **http://localhost:5173** in your browser.

> **Why a separate dev server?** The API server (`dplayer-api`) currently serves only the JSON API —
> static file hosting is not wired in. Production release builds are bundled via Tauri (the desktop
> shell) and don't require a separate Node.js process. For now, the dev server is the supported
> browser path.

---

## First-run FTUX

If `DISCOGS_TOKEN` is not set when the API starts, the frontend automatically redirects you to
`/setup`. On that page:

1. Paste your Discogs personal access token into the field
2. Click **Save**
3. The app redirects to the home page and starts loading your collection

---

## Step 5 — Sync your collection

Either:

- Click **Sync** in the navigation bar, or
- Run `dplayer sync` in a terminal

The initial sync fetches all releases and wantlist items from Discogs. Subsequent syncs are
incremental and much faster.

---

## Done? Verify it works

Open **http://localhost:5173** in your browser and click **Spin**. If it returns a record from
your collection, you're all set. You can also verify from the terminal:

```bash
dplayer status
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| "API not reachable" / blank page | Confirm `dplayer-api` is running and check for errors in that terminal |
| `ModuleNotFoundError: fastapi` | Run `pip install -e ".[web]"` — you installed the core profile only |
| `npm: command not found` | Install Node.js 20+ from [nodejs.org](https://nodejs.org) |
| Token errors after save | Check that the token is a valid Discogs personal access token (not OAuth) |
| Port 8768 already in use | Another process is using that port; kill it or restart your machine |

---

## What's next

- **Spin** — the Spin button picks a random record from your collection
- **Value dashboard** — see your collection's market value and top movers
- **Wantlist** — browse and filter records you're looking for
- **Playback** — optional Spotify or YouTube Music integration; see [Token Setup](token_setup.md)
