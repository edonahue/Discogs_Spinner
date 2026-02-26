# Spotify CLI Auth Walkthrough

This guide covers how to authenticate Spotify from this repo when `dplayer` is not found on `PATH`.

Prerequisite: install the optional Spotify addon profile first:

```bash
pip install -e ".[spotify]"
```

## 1) Why `dplayer` was not found

`dplayer` is a console script defined in `pyproject.toml`. It is only available after installing the package (usually editable install) in your active Python environment.

## 2) Run from repo immediately (no console-script install required)

From repo root:

```bash
source .venv/bin/activate
PYTHONPATH=src python -m discogs_player.main auth spotify
```

If you want JSON output:

```bash
source .venv/bin/activate
PYTHONPATH=src python -m discogs_player.main auth spotify --json
```

## 3) Preferred setup (so `dplayer` works)

From repo root:

```bash
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
dplayer --help
```

If `.venv` does not exist yet:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

After this, auth is:

```bash
dplayer auth spotify
```

## 4) Required Spotify app settings

In Spotify Developer Dashboard:

1. Create/select your app.
2. Add redirect URI:
   - `http://127.0.0.1:8765/callback`
3. Save.

Set credentials in shell:

```bash
export SPOTIFY_CLIENT_ID='your_client_id'
export SPOTIFY_SECRET='your_client_secret'
# Legacy alias still supported:
# export SPOTIFY_CLIENT_SECRET='your_client_secret'
```

Then run:

```bash
dplayer auth spotify --listen-host 127.0.0.1 --listen-port 8765
```

If browser shows `INVALID_CLIENT` / `Invalid redirect URI`, ensure Spotify app redirect URI is exactly:

```text
http://127.0.0.1:8765/callback
```

The command prints an authorization URL. Open it in a browser, approve, and wait for callback completion.

Manual entry mode (no local listener) is also supported:

```bash
# Interactive paste (URL or code)
dplayer auth spotify --manual

# Non-interactive/manual scripting
dplayer auth spotify --manual --callback-url 'http://127.0.0.1:8765/callback?code=...&state=...'
dplayer auth spotify --manual --code 'AQD...'
```

Prefer `--callback-url` when possible because it validates OAuth state. `--code` is kept for constrained/headless cases where only the code is available.

## 5) SSH/headless flow (recommended)

If the command runs on a remote machine but browser is on your local machine, use SSH local port forwarding:

```bash
ssh -L 8765:127.0.0.1:8765 <user>@<remote-host>
```

Then on the remote shell (same SSH session):

```bash
cd ~/projects/discogs_player
source .venv/bin/activate
dplayer auth spotify --listen-host 127.0.0.1 --listen-port 8765
```

Open the printed Spotify URL in a browser on your local machine. The callback to `127.0.0.1:8765` tunnels back to the remote host.

## 6) Validate auth

Run:

```bash
dplayer devices --json
dplayer auth spotify-doctor --json
```

If auth is valid, you should get device JSON (or an empty devices list without auth errors).

## 7) Troubleshooting

- `Command 'dplayer' not found`:
  - Activate venv and run `pip install -e .`, or use module form:
    - `PYTHONPATH=src python -m discogs_player.main ...`

- `Spotify client id is required` or `Spotify client secret is required`:
  - Export `SPOTIFY_CLIENT_ID` and `SPOTIFY_SECRET` (legacy: `SPOTIFY_CLIENT_SECRET`).

- Callback timeout:
  - Ensure redirect URI in Spotify app exactly matches host/port/path used in command.
  - Ensure SSH tunnel is active if browser is not on the same machine.
  - CLI now prompts for manual callback URL/code entry automatically on callback timeout/bind failures.

- Temporary-token-only fallback (not recommended for normal use):
  - You can set `SPOTIFY_ACCESS_TOKEN`, but it expires and can break later playback/matching.
