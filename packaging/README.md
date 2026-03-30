# Packaging

Artifacts for building distributable packages.

## `deb/`

Files for the GTK4 Linux desktop `.deb` package:

| File | Purpose |
|------|---------|
| `dplayer-gui.desktop` | Desktop launcher (shows app in application menu) |
| `postinst` | Post-install script — creates `/opt/discogs-spinner/venv` and installs the bundled wheelhouse offline |

Built by `scripts/build_deb.sh` using `fpm`. See `desktop_shell/README.md` for the
full build workflow. The Debian wheelhouse includes the local `web` profile so
`dplayer-api` works offline, and it must be built with Python 3.10 so
environment-marked dependencies match the runtime on Ubuntu 22.04.
