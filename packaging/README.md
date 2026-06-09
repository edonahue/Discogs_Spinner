# Packaging

Artifacts for building distributable packages.

## `deb/`

Files for the GTK4 Linux desktop `.deb` package:

| File | Purpose |
|------|---------|
| `dplayer-gui.desktop` | Desktop launcher (shows app in application menu) |
| `io.github.edonahue.DiscogsSpinner.metainfo.xml` | AppStream metadata for Linux software-center listings |
| `postinst` | Post-install script — creates `/opt/discogs-spinner/venv` and installs the bundled wheelhouse offline |

Built by `scripts/build_deb.sh` using `fpm`. See `desktop_shell/README.md` for the
full build workflow. The Debian wheelhouse includes the local `web` profile so
`dplayer-api` works offline, and it must be built with Python 3.10 so
environment-marked dependencies match the runtime on Ubuntu 22.04.

Before publishing a GTK `.deb`, run:

```bash
python3 scripts/validate_linux_packaging_metadata.py
```

The `Installer Build` workflow also runs `lintian` against the GTK `.deb` so
desktop metadata and package-level issues are caught before release assets are
published.

Related docs:

- [Desktop shell README](../desktop_shell/README.md)
- [Debian quickstart](../docs/quickstart_debian.md)
- [Public release runbook](../docs/PUBLIC_RELEASE_RUNBOOK.md)
- [Current stable release notes](../docs/releases/v0.2.2.md)
- [Store submissions guide](../docs/STORE_SUBMISSIONS.md)
