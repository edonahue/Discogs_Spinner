# Quickstart (Windows)

This guide targets first-time users installing `discogs_player` on Windows.

## 1) Prerequisites

- Windows 10/11
- Python 3.10+ (`py --version`)
- Git
- Discogs account + personal token ([how to get one](token_setup.md))
- Optional: Spotify account (for playback/matching features — [how to set up](token_setup.md#spotify-api-credentials))

## 2) Clone and install

Open PowerShell:

```powershell
git clone https://github.com/edonahue/Discogs_Spinner.git
cd Discogs_Spinner
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

Optional Spotify features:

```powershell
pip install -e ".[spotify]"
```

## 3) Configure Discogs token

Get your personal access token at [discogs.com/settings/developers](https://www.discogs.com/settings/developers) (Personal Access Tokens → Generate new token).

```powershell
$env:DISCOGS_TOKEN = "your_discogs_personal_token"
dplayer setup
```

## 4) First sync and verification

```powershell
dplayer sync
dplayer status
dplayer list --limit 10
```

## 5) Optional Spotify onboarding

First, create a Spotify app and get your Client ID + Secret at [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard). Add `http://127.0.0.1:8765/callback` as a redirect URI. See [token_setup.md](token_setup.md#spotify-api-credentials) for full steps.

```powershell
$env:SPOTIPY_CLIENT_ID = "your_client_id"
$env:SPOTIPY_CLIENT_SECRET = "your_client_secret"
$env:SPOTIPY_REDIRECT_URI = "http://127.0.0.1:8765/callback"
dplayer auth spotify-doctor
dplayer auth spotify --open-browser --listen-host 127.0.0.1 --listen-port 8765
dplayer devices --json
```

Safe first play fallback:

```powershell
dplayer play --last-spin --open
```

## 6) Troubleshooting

- If script activation is blocked:
  - run PowerShell as current user and execute
    `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`
- Use issue templates for support:
  - install failures
  - auth/setup failures
  - playback failures
