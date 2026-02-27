"""GTK entrypoint for Discogs Player."""

from __future__ import annotations

import argparse
import sys
from typing import Optional

GUI_APT_INSTALL_CMD = (
    "sudo apt update && sudo apt install -y "
    "python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 libadwaita-1-0 "
    "gir1.2-gdkpixbuf-2.0 xvfb"
)


def _missing_gui_dependency_message(module_name: str) -> str:
    return "\n".join(
        [
            f"Missing GUI dependency: {module_name}",
            "",
            "Install required Pop!_OS GUI packages:",
            f"  {GUI_APT_INSTALL_CMD}",
        ]
    )


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dplayer-gui", description="Discogs Player GTK UI"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Maximum releases to render (0 = all releases)",
    )
    parser.add_argument(
        "--no-preload-covers",
        action="store_true",
        help="Skip cover prefetch and render placeholders only",
    )
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Load releases once, print JSON report, and exit",
    )
    parser.add_argument(
        "--timing",
        action="store_true",
        help="Print per-operation latency samples to stderr (browse-load and wantlist-load hotspots)",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    try:
        import gi
    except ModuleNotFoundError as exc:
        module_name = exc.name or "gi"
        print(_missing_gui_dependency_message(module_name), file=sys.stderr)
        return 1

    try:
        gi.require_version("Gtk", "4.0")
        gi.require_version("Adw", "1")
    except ValueError as exc:
        print(f"GTK/libadwaita runtime not available: {exc}", file=sys.stderr)
        print(_missing_gui_dependency_message("gi.repository"), file=sys.stderr)
        return 1

    try:
        from discogs_player.ui.main_window import DiscogsPlayerApp
    except ModuleNotFoundError as exc:
        module_name = exc.name or "unknown"
        print(f"Failed to import GUI module dependency: {module_name}", file=sys.stderr)
        return 1

    if args.timing:
        import importlib
        _mw = importlib.import_module("discogs_player.ui.main_window")
        set_timing_enabled = getattr(_mw, "set_timing_enabled", None)
        if set_timing_enabled is not None:
            set_timing_enabled(True)

    app = DiscogsPlayerApp(
        limit=max(0, int(args.limit)),
        preload_covers=not args.no_preload_covers,
        smoke_test=bool(args.smoke_test),
    )
    app.run(["dplayer-gui"])
    return int(app.exit_code)


if __name__ == "__main__":
    raise SystemExit(main())
