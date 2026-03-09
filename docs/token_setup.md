# Token Setup Guide

Quick reference for getting the API credentials Discogs Spinner needs.

---

## Discogs Personal Access Token

Required for all users. Lets the app read your collection, wantlist, and market data.

1. Log in to [discogs.com](https://www.discogs.com)
2. Go to **Settings → Developers**:
   [https://www.discogs.com/settings/developers](https://www.discogs.com/settings/developers)
3. Scroll to **Personal Access Tokens** and click **Generate new token**
4. Copy the token — it won't be shown again

Set it in your shell:

```bash
export DISCOGS_TOKEN="your_token_here"
```

Or add it to your shell profile (`~/.bashrc`, `~/.zshrc`, etc.) so it persists across sessions.

> **Privacy:** Your token grants read/write access to your Discogs account. Keep it out of public repos and shared dotfiles.

---

## Spotify API Credentials

Optional. Only needed if you want Spotify Connect playback control from inside the app.

You need three values: **Client ID**, **Client Secret**, and a **redirect URI**.

### Step 1 — Create a Spotify app

1. Log in to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Click **Create app**
3. Fill in any name and description (e.g. "Discogs Spinner local")
4. Under **Redirect URIs**, add exactly:
   ```
   http://127.0.0.1:8765/callback
   ```
5. Check **Web API** and **Web Playback SDK**, then click **Save**

### Step 2 — Copy your credentials

On the app detail page, click **Settings** to reveal:
- **Client ID** — visible immediately
- **Client Secret** — click "View client secret"

### Step 3 — Set environment variables

```bash
export SPOTIPY_CLIENT_ID="your_client_id"
export SPOTIFY_SECRET="your_client_secret"
export SPOTIPY_REDIRECT_URI="http://127.0.0.1:8765/callback"
```

Add these to your shell profile to persist them.

### Step 4 — Authorize

```bash
dplayer auth spotify --open-browser --listen-host 127.0.0.1 --listen-port 8765
```

This opens a browser window for one-time OAuth authorization. After approving, the token is stored locally and refreshed automatically.

Run `dplayer auth spotify-doctor` at any time to verify connectivity.

> **Privacy:** Your Spotify credentials grant playback control only. The app never accesses your Spotify listening history or account details beyond active device state.
