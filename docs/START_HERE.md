# Where should I start?

Three quick questions will point you at the right setup guide.

---

## Which setup is right for you?

### Question 1 — What OS are you on?

- **Windows** → go to Question 2
- **macOS** → go to Question 3
- **Linux (Debian/Ubuntu)** → [Debian Quickstart](quickstart_debian.md) (~10 min)

### Question 2 — Windows: do you want a full desktop GUI?

| I want… | Go to |
|---------|-------|
| The easiest possible start (browser-based UI) | [Web App Quickstart](quickstart_web.md) (~10 min) |
| A native Windows installer (Tauri app) | [Windows Quickstart](quickstart_windows.md) (~5 min) |
| The full GTK desktop GUI via WSL2 | [WSL2 Quickstart](quickstart_wsl2.md) (~15 min) |
| Just the CLI (`dplayer` in PowerShell) | [Windows Quickstart](quickstart_windows.md) (~5 min) |

### Question 3 — macOS: what kind of setup do you want?

| I want… | Go to |
|---------|-------|
| A native macOS installer | [macOS Quickstart](quickstart_macos.md) (~5 min) |
| The easiest possible start (browser-based UI) | [Web App Quickstart](quickstart_web.md) (~10 min) |
| CLI only (`dplayer` in Terminal) | [macOS Quickstart](quickstart_macos.md) (~10 min, source install) |

---

## Decision table

| OS | Interface | Experience | Guide | Est. time |
|----|-----------|------------|-------|-----------|
| Any | Web browser | Any | [Web App Quickstart](quickstart_web.md) | ~10 min |
| Windows | Native installer | Any | [Windows Quickstart](quickstart_windows.md) | ~5 min |
| Windows | Desktop GUI | Comfortable with WSL2 | [WSL2 Quickstart](quickstart_wsl2.md) | ~15 min |
| Linux | Desktop GUI + CLI | Any | [Debian Quickstart](quickstart_debian.md) | ~10 min |
| macOS | Native installer | Any | [macOS Quickstart](quickstart_macos.md) | ~5 min |
| macOS | CLI | Comfortable with Terminal | [macOS Quickstart](quickstart_macos.md) | ~10 min |

---

## What to expect at the end of each path

### Web App (~10 min)
Two terminals running (`dplayer-api` + `npm run dev`), browser open at `http://localhost:5173`.
Proving it works: the Spin button returns a record from your collection.

### Windows native installer (~5 min)
Installer runs, Setup Wizard appears on first launch for token entry.
Proving it works: `dplayer status` in PowerShell shows your collection count.

### Linux desktop GUI (~10 min)
`discogs-player-gui` opens a GTK4 window with your collection loaded.
Proving it works: `dplayer status` shows collection count and last sync date.

### WSL2 GUI (~15 min)
`dplayer-gui` opens a GTK4 window on your Windows desktop via WSLg.
Proving it works: the window appears and displays your collection after `dplayer sync`.

### macOS native installer (~5 min)
`Discogs Spinner.app` opens from `/Applications` and the setup flow accepts your token.
Proving it works: the app syncs and loads your collection without errors.

---

After any path: run `dplayer status` — if it shows your collection count and last sync date, you're all set.

Need a Discogs token first? [Token setup →](token_setup.md)
