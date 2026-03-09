# Packaging

Artifacts for building distributable packages.

## `deb/`

Files for the GTK4 Linux desktop `.deb` package:

| File | Purpose |
|------|---------|
| `dplayer-gui.desktop` | Desktop launcher (shows app in application menu) |
| `postinst` | Post-install script — sets executable permissions |

Built by `scripts/build_deb.sh` using `fpm`. See `desktop_shell/README.md` for the
full build workflow.
