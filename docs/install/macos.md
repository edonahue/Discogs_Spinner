# macOS Installation — Gatekeeper Bypass

Discogs Spinner is not yet notarized with Apple. macOS will block the first launch.

## Right-click method (recommended)

1. Open the `.dmg` and drag **Discogs Spinner** to `/Applications`.
2. In Finder, **right-click** (or Control-click) the app icon and choose **Open**.
3. Click **Open** in the dialog. This grants a permanent exception — normal double-click works from here on.

## Terminal one-liner (alternative)

```bash
xattr -d com.apple.quarantine /Applications/Discogs\ Spinner.app
```

Then double-click to launch as normal.

## Long-term plan

Full Apple notarization will be added in a future release after joining the Apple Developer Program.
