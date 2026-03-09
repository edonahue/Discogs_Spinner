# Quickstart (Windows + WSL2 GUI)

Run the full Discogs Spinner GTK4 desktop GUI on Windows via WSL2 + WSLg.

> **Windows 11 required.** WSLg (the GUI layer) ships with Windows 11 build 22000+.
> Windows 10 does not include WSLg; CLI-only via [quickstart_windows.md](quickstart_windows.md).

---

> **Estimated time:** ~15 minutes

## 1) Enable WSL2 and install Ubuntu

Open PowerShell **as Administrator** and run:

```powershell
wsl --install
```

This single command enables WSL2, installs Ubuntu, and sets up WSLg (the GUI layer). Restart
your machine when prompted.

After reboot, Ubuntu launches automatically to complete setup (create a username and password).

---

## 2) Install GTK4 system packages inside Ubuntu

Open an Ubuntu terminal (search "Ubuntu" in the Start menu) and run:

```bash
sudo apt update && sudo apt install -y \
  python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 libadwaita-1-0 \
  gir1.2-gdkpixbuf-2.0 xvfb
```

---

## 3) Clone the repo inside WSL2

**Important:** Clone inside the WSL2 filesystem (not `/mnt/c/...`) for best performance.

```bash
cd ~
git clone https://github.com/edonahue/Discogs_Spinner.git
cd Discogs_Spinner
```

---

## 4) Create a venv and install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

Optional Spotify features:

```bash
pip install -e ".[spotify]"
```

---

## 5) Set your Discogs token

Get your personal access token at [discogs.com/settings/developers](https://www.discogs.com/settings/developers)
(Personal Access Tokens → Generate new token).

```bash
export DISCOGS_TOKEN="your_discogs_personal_token"
```

To persist it across sessions, add it to `~/.bashrc`:

```bash
echo 'export DISCOGS_TOKEN="your_discogs_personal_token"' >> ~/.bashrc
source ~/.bashrc
```

---

## 6) First sync

```bash
dplayer sync
dplayer status
```

---

## 7) Launch the GUI

```bash
dplayer-gui
```

WSLg passes the GTK4 window through to your Windows desktop — it appears as a native-feeling
window with no extra setup required.

---

## Done? Verify it works

```bash
dplayer status
dplayer spin
```

If `dplayer status` shows your collection count and last sync date, you're all set.

## Troubleshooting

**GUI window doesn't appear**
- Confirm you're on Windows 11 build 22000+: run `winver` in PowerShell.
- Make sure WSL2 is fully updated: `wsl --update` in PowerShell (as Administrator).
- Try `echo $DISPLAY` inside Ubuntu — WSLg sets this automatically; if it's empty, restart WSL: `wsl --shutdown` then reopen Ubuntu.

**GTK errors on launch**
- Re-run the apt install from step 2 to ensure all packages installed correctly.
- Confirm the venv is active (`source .venv/bin/activate`) before running `dplayer-gui`.

**`DISCOGS_TOKEN` not set**
- You'll see an auth error on first sync. Add the export to `~/.bashrc` (step 5) and reopen your terminal.

**Slow file I/O**
- This happens when the repo is on the Windows filesystem (`/mnt/c/...`). Re-clone inside `~/` (WSL2 filesystem) for normal performance.

---

For the Windows CLI-only path (no WSL2), see [quickstart_windows.md](quickstart_windows.md).
