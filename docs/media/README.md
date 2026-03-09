# README Media Assets

This directory stores visual assets used in the top section of `README.md`.

## Asset Layout

- `gif/product-demo.gif`: featured product demo GIF shown at the top of the README.
- `screenshots/01-browse-gallery.png`
- `screenshots/02-spin-result.png`
- `screenshots/03-market-value-dashboard.png`
- `screenshots/04-wantlist-view.png`
- `screenshots/05-setup-wizard.png`

## Capture Real Screenshots

Preferred: headless capture from the live GTK4 app (no desktop session required).

```bash
python3 scripts/headless_screenshot.py
```

Runs under Xvfb at 1440×900, navigates all views automatically, and assembles
the GIF. Requires `Xvfb` (system) and `python-xlib` + `Pillow` (venv).

Legacy semi-automated script (X11/Wayland, requires desktop session):

```bash
bash scripts/capture_readme_media.sh
```

## Synthetic Fallback

If the app cannot be launched, regenerate synthetic placeholder assets:

```bash
python3 scripts/generate_readme_media.py
```

Pulls real local collection entries through `dplayer list --json` when available
and renders placeholder PNGs + demo GIF using PIL.

## Size Targets

- Demo GIF: under 8 MB (GitHub renders inline up to ~10 MB)
- Screenshots: under 700 KB each (1440×900 headless PNG; lossless optipng if needed)
