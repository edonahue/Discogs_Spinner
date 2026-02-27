# README Media Assets

This directory stores visual assets used in the top section of `README.md`.

## Asset Layout

- `gif/product-demo.gif`: featured product demo GIF shown at the top of the README.
- `screenshots/01-browse-gallery.png`
- `screenshots/02-wantlist-priority.png`
- `screenshots/03-market-value-dashboard.png`
- `screenshots/04-cli-to-ui-flow.png`

## Regenerate Assets

From repository root:

```bash
python3 scripts/generate_readme_media.py
```

The generator script:

- pulls real local collection entries through `dplayer list --json` when available,
- applies selective redaction to artist/title text,
- generates screenshot PNGs,
- exports an optimized demo GIF.

## Redaction Policy

Media is generated from real local data but selectively redacted before export:

- artist/title strings are masked,
- no auth tokens or credentials are included,
- no personal account identifiers are rendered.

## Size Targets

- Demo GIF target: under `15 MB`
- Screenshot targets: compressed PNGs suitable for fast README load
