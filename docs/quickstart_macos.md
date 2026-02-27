# Quickstart (macOS)

This guide targets first-time users installing `discogs_player` on macOS.

## 1) Prerequisites

- macOS 13+
- Homebrew installed
- Discogs account + personal token
- Optional: Spotify account (for playback/matching features)

Install base tools:

```bash
brew update
brew install python@3.12 git
```

## 2) Clone and install

```bash
git clone https://github.com/edonahue/Discogs_Spinner.git
cd Discogs_Spinner
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

Optional Spotify features:

```bash
pip install -e ".[spotify]"
```

## 3) Configure Discogs token

```bash
export DISCOGS_TOKEN="your_discogs_personal_token"
dplayer setup
```

## 4) First sync and verification

```bash
dplayer sync
dplayer status
dplayer list --limit 10
```

## 5) Optional Spotify onboarding

```bash
dplayer auth spotify-doctor
dplayer auth spotify --open-browser --listen-host 127.0.0.1 --listen-port 8765
dplayer devices --json
```

Safe first play fallback:

```bash
dplayer play --last-spin --open
```

## 6) Notes

- Keep this as a CLI-first setup path unless a signed macOS app build is provided.
- If browser callback fails, use manual callback options from `dplayer auth spotify --help`.

## 7) Gatekeeper and Signing Status (2026-02-26)

- Current release artifacts are tarball bundles (`core` and `plus`), not a signed `.app` installer.
- Code signing and notarization are not yet in place for this RC channel.
- If you launch unsigned binaries/scripts from Finder, Gatekeeper may block first launch with a developer verification warning.
- Pilot workaround:
  - use right-click -> Open for first launch, then confirm,
  - if needed for testing only, remove quarantine attribute:
    `xattr -dr com.apple.quarantine <path-to-extracted-artifact-or-launcher>`

## 8) Signing/Notarization TODOs

1. Define signing identity and certificate storage policy for CI.
2. Add a codesign step for macOS release artifacts in tagged-release workflow.
3. Add notarization submission + staple workflow and failure handling.
4. Publish user-facing Gatekeeper troubleshooting section once signed builds ship.
