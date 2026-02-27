# README Media Assets

This directory stores visual assets used in the top section of `README.md`.

## Asset Layout

- `gif/product-demo.gif`: featured product demo GIF shown at the top of the README.
- `screenshots/01-browse-gallery.png`
- `screenshots/02-spin-result.png`
- `screenshots/03-market-value-dashboard.png`
- `screenshots/04-wantlist-view.png`

## Capture Real Screenshots

Preferred: capture real screenshots and a GIF from the running GTK4 app.

```bash
bash scripts/capture_readme_media.sh
```

Supports X11 and Wayland (Pop!OS / COSMIC). Guided semi-automated mode prompts
for navigation on Wayland; fully automated on X11 with `xdotool`.

## Synthetic Fallback

If the app cannot be launched, regenerate synthetic placeholder assets:

```bash
python3 scripts/generate_readme_media.py
```

Pulls real local collection entries through `dplayer list --json` when available
and renders placeholder PNGs + demo GIF using PIL.

## Size Targets

- Demo GIF: under 8 MB (GitHub renders inline up to ~10 MB)
- Screenshots: under 200 KB each
