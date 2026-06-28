# Windows Tauri FTUX Validation Checklist

Run this checklist once on a clean Windows machine before approving the Windows public installer release.

## Pre-conditions

- [ ] Fresh Windows 10 or 11 machine (or clean VM), no Discogs token pre-configured
- [ ] Downloaded `Discogs.Spinner_0.2.3_x64-setup.exe` from [GitHub Releases](https://github.com/edonahue/Discogs_Spinner/releases)

## Install

- [ ] Run the installer; accept the SmartScreen prompt ("More info → Run anyway")
- [ ] App launches automatically after install; Tauri window opens
- [ ] Browser/webview shows the **Setup** page, not the collection view

## Token setup

- [ ] Enter your Discogs personal token in the Setup page
- [ ] Click **Save** / **Submit**
- [ ] App redirects to the **Home** page showing release count = 0

## First sync

- [ ] Click **Sync Collection** on the Home page
- [ ] Status bar shows syncing state (e.g. "Syncing… page 3 of 12"), then updates
- [ ] Navigate to **Collection**; releases load without errors

## Playback (optional)

- [ ] Open a release detail view
- [ ] Confirm the YouTube search link opens in the system browser

## Pass criteria

All boxes above are checked, with no crashes or persistent blank screens at any step.

---

*Last validated: — (fill in date and Windows version when completed)*
