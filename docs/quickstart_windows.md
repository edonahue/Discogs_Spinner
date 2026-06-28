# Quickstart (Windows)

This guide targets first-time users installing `discogs_player` on Windows.

## 1) Prerequisites

> **Estimated time:** ~5 minutes

- Windows 10/11
- Discogs account + personal token ([how to get one](token_setup.md))
- Optional: Spotify account (for playback/matching features — [how to set up](token_setup.md#spotify-api-credentials))

## 2) Install the native app

**Option A — WinGet (recommended if you already use winget):**

```powershell
winget install ErichDonahue.SpinnerforDiscogs
```

This installs the same signed package available on GitHub Releases and keeps the app updatable via `winget upgrade`.

**Option B — Direct download:**

- Recommended installer: [Discogs Spinner_0.2.3_x64-setup.exe](https://github.com/edonahue/Discogs_Spinner/releases/download/v0.2.3/Discogs.Spinner_0.2.3_x64-setup.exe)
- MSI installer: [Discogs Spinner_0.2.3_x64_en-US.msi](https://github.com/edonahue/Discogs_Spinner/releases/download/v0.2.3/Discogs.Spinner_0.2.3_x64_en-US.msi)
- Checksums: [CHECKSUMS-INSTALLERS.txt](https://github.com/edonahue/Discogs_Spinner/releases/download/v0.2.3/CHECKSUMS-INSTALLERS.txt)
- Fallback release page: [GitHub Releases](https://github.com/edonahue/Discogs_Spinner/releases/latest)

Run the installer and launch **Discogs Spinner** from the Start menu.

What you may see:

- Windows may show a SmartScreen warning because the app is not signed yet.
- If that happens, use `More info` -> `Run anyway`.

## 3) First launch and token setup

On first launch, the app should open directly into the setup flow.

- Paste your Discogs personal access token
- Save the token
- Start your first collection sync from the app
- Confirm the collection view loads without errors

What success looks like:

- you reach the setup wizard instead of a blank screen
- your first sync completes
- the collection view opens with your records visible

## 4) Optional Spotify onboarding

If you want Spotify features in the CLI or web stack, create a Spotify app and get your Client ID + Secret at [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard). Add `http://127.0.0.1:8765/callback` as a redirect URI. See [token_setup.md](token_setup.md#spotify-api-credentials) for full steps.

```powershell
$env:SPOTIPY_CLIENT_ID = "your_client_id"
$env:SPOTIFY_SECRET = "your_client_secret"
$env:SPOTIPY_REDIRECT_URI = "http://127.0.0.1:8765/callback"
dplayer auth spotify-doctor
dplayer auth spotify --open-browser --listen-host 127.0.0.1 --listen-port 8765
dplayer devices --json
```

Safe first play fallback from the CLI:

```powershell
dplayer play --last-spin --open
```

## 5) PowerShell / CLI path (advanced)

If you want the Python CLI in PowerShell in addition to the native app, install it from source:

```powershell
git clone https://github.com/edonahue/Discogs_Spinner.git
cd Discogs_Spinner
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
pip install -e ".[spotify]"
```

Equivalent CLI-first onboarding:

```powershell
dplayer setup
dplayer sync
dplayer status
dplayer list --limit 10
```

If you want the Linux GTK app on Windows, use [WSL2 Quickstart](quickstart_wsl2.md).

## Done? Verify it works

- Native app path: the collection loads after setup and sync, with no blank screen or crash
- CLI path: `dplayer status` shows your collection count and last sync date

For a clean-machine installer checklist, use [Windows FTUX Validation](validation/windows_tauri_ftux.md).

## 6) Troubleshooting

- If script activation is blocked:
  - run PowerShell as current user and execute
    `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`
- If the installer is blocked by SmartScreen, use `More info` -> `Run anyway`
- Use issue templates for install, auth/setup, or playback failures
