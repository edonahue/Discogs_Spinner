# macOS Installer FTUX Validation Checklist

Run this checklist once on a clean macOS machine before approving a signed/notarized `v1.0.0` release.

## Pre-conditions

- [ ] Clean macOS 13+ machine
- [ ] Downloaded the latest `.dmg` from the stable release page
- [ ] No Discogs token pre-configured

## Install

- [ ] Open the `.dmg`
- [ ] Drag **Discogs Spinner.app** into `/Applications`
- [ ] Launch the app from `/Applications`
- [ ] Confirm the normal path does not require a quarantine-removal workaround

## Token setup

- [ ] App opens into the setup flow on first launch
- [ ] Discogs token can be entered and saved
- [ ] App proceeds to a usable post-setup state without a blank screen or crash

## First sync

- [ ] Start a collection sync from the app
- [ ] Collection view loads without errors after sync
- [ ] Browse or spin works on at least one release

## Optional provider check

- [ ] Optional provider controls fail gracefully when credentials or devices are unavailable

## Pass criteria

All boxes above are checked, with no crash, persistent blank state, or misleading first-launch instructions.

---

*Last validated: — (fill in date, macOS version, and hardware when completed)*
