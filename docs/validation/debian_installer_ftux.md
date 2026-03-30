# Debian Installer FTUX Validation Checklist

Run this checklist once on a clean Debian/Ubuntu desktop machine before approving a `v1.0.0` release.

## Pre-conditions

- [ ] Clean Debian 12+ or Ubuntu equivalent desktop machine
- [ ] Downloaded the recommended GTK `.deb` from the stable release page
- [ ] No Discogs token pre-configured

## Install

- [ ] Install the package with `apt` or the desktop software installer
- [ ] Launch **Discogs Spinner** from the app menu
- [ ] Confirm the app opens without needing a terminal-first workaround

## Token setup

- [ ] App opens into the setup flow on first launch
- [ ] Discogs token can be entered and saved
- [ ] App proceeds to a usable post-setup state without a blank screen or crash

## First sync

- [ ] Start a collection sync from the app
- [ ] Collection and wantlist views load without errors after sync
- [ ] Browse or spin works on at least one release

## Optional provider check

- [ ] Optional provider controls or auth flows fail gracefully when credentials or devices are unavailable

## Pass criteria

All boxes above are checked, with no crash, missing dependency surprise, or misleading install/setup instructions.

---

*Last validated: — (fill in date, distro, desktop session, and package source when completed)*
