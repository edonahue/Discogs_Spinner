"""GTK entrypoint for Spinner for Discogs."""

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
            "Install required Debian/Ubuntu/WSL2 GUI packages:",
            f"  {GUI_APT_INSTALL_CMD}",
        ]
    )


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dplayer-gui", description="Spinner for Discogs GTK UI"
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
        help="Deprecated alias for --cover-preload off",
    )
    parser.add_argument(
        "--cover-preload",
        choices=("off", "visible", "all"),
        default="visible",
        help=(
            "Cover prefetch strategy: off skips prefetch, visible warms nearby "
            "covers after first paint, all blocks load while warming every cover"
        ),
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
    parser.add_argument(
        "--perf-report",
        action="store_true",
        help="Include CPU/memory/performance profile fields in smoke-test JSON output",
    )
    parser.add_argument(
        "--idle-probe",
        type=int,
        default=0,
        metavar="SECONDS",
        help=(
            "Load the GTK UI, force background-idle suspension, sample CPU/memory "
            "for SECONDS, print a JSON report, and exit"
        ),
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    try:
        import gi
    except ImportError as exc:
        # ModuleNotFoundError (gi absent) or a broken PyGObject install (e.g. a
        # half-built _gi extension) both land here; show the install guidance
        # instead of letting a raw traceback escape.
        module_name = getattr(exc, "name", None) or "gi"
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

    cover_preload = "off" if args.no_preload_covers else str(args.cover_preload)
    app = DiscogsPlayerApp(
        limit=max(0, int(args.limit)),
        preload_covers=cover_preload == "all",
        smoke_test=bool(args.smoke_test),
        perf_report=bool(args.perf_report),
        idle_probe_seconds=max(0, int(args.idle_probe)),
    )
    app.run(["dplayer-gui"])
    return int(app.exit_code)


if __name__ == "__main__":
    raise SystemExit(main())
