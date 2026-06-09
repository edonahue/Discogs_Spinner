# Where should I start?

Three quick questions will point you at the fastest successful setup path.

You will need a Discogs account and personal access token before the app can sync your collection. Get one from [Discogs Settings → Developers](https://www.discogs.com/settings/developers), then keep it ready for the first-run setup wizard.

---

## Which setup is right for you?

### Question 1 — What OS are you on?

- **Windows** → go to Question 2
- **macOS** → go to Question 3
- **Linux** → [Debian/Linux Quickstart](quickstart_debian.md) (~10 min)

### Question 2 — Windows: do you want a full desktop GUI?

| I want… | Go to |
|---------|-------|
| A native Windows installer (Tauri app) | [Windows Quickstart](quickstart_windows.md) (~5 min) |
| A no-install browser fallback | [Web App Quickstart](quickstart_web.md) (~10 min) |
| The full GTK desktop GUI via WSL2 | [WSL2 Quickstart](quickstart_wsl2.md) (~15 min) |
| Just the CLI (`dplayer` in PowerShell) | [Windows Quickstart](quickstart_windows.md) (~5 min) |

### Question 3 — macOS: what kind of setup do you want?

| I want… | Go to |
|---------|-------|
| A native macOS installer | [macOS Quickstart](quickstart_macos.md) (~5 min) |
| A no-install browser fallback | [Web App Quickstart](quickstart_web.md) (~10 min) |
| CLI only (`dplayer` in Terminal) | [macOS Quickstart](quickstart_macos.md) (~10 min, source install) |

---

## Decision table

| OS | Interface | Experience | Guide | Est. time |
|----|-----------|------------|-------|-----------|
| Any | Web browser | Fallback / no-install path | [Web App Quickstart](quickstart_web.md) | ~10 min |
| Windows | Native installer | Any | [Windows Quickstart](quickstart_windows.md) | ~5 min |
| Windows | Desktop GUI | Comfortable with WSL2 | [WSL2 Quickstart](quickstart_wsl2.md) | ~15 min |
| Linux | Desktop GUI + CLI | Any | [Debian/Linux Quickstart](quickstart_debian.md) | ~10 min |
| macOS | Native installer | Any | [macOS Quickstart](quickstart_macos.md) | ~5 min |
| macOS | CLI | Comfortable with Terminal | [macOS Quickstart](quickstart_macos.md) | ~10 min |

---

## What to expect at the end of each path

The goal is the same on every platform: install, paste your Discogs token, sync once, see your records, and use Spin to choose something to play.

### Web App (~10 min)
Two terminals running (`dplayer-api` + `npm run dev`), browser open at `http://localhost:5173`.
Proving it works: the Spin button returns a record from your collection.

### Windows native installer (~5 min)
Installer finishes, the Setup Wizard appears on first launch, and your first sync ends with the collection view loaded.
Proving it works: you can browse your collection in the app, and `dplayer status` in PowerShell also shows your collection count.

### Linux desktop GUI (~10 min)
The Snap Store app, GTK desktop package, or portable AppImage opens, the setup flow accepts your token, and the collection view loads after sync.
Proving it works: the app shows your collection and `dplayer status` shows collection count and last sync date.

### WSL2 GUI (~15 min)
`dplayer-gui` opens a GTK4 window on your Windows desktop via WSLg.
Proving it works: the window appears and displays your collection after `dplayer sync`.

### macOS native installer (~5 min)
`Discogs Spinner.app` opens from `/Applications`, the setup flow accepts your token, and the collection view loads after sync.
Proving it works: the app syncs and loads your collection without errors.

---

After any path: run `dplayer status` — if it shows your collection count and last sync date, you're all set.

Need a Discogs token first? [Token setup →](token_setup.md)
