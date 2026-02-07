"""CLI entrypoint for discogs_player."""

from __future__ import annotations

import sys
from typing import Optional


def _missing_dependency_message(module_name: str) -> str:
    return "\n".join(
        [
            f"Missing Python dependency: {module_name}",
            "",
            "Install required system packages on Pop!_OS:",
            "  sudo apt update && sudo apt install -y python3 python3-venv python3-pip libsecret-1-0",
            "",
            "Then install project dependencies:",
            "  python3 -m venv .venv",
            "  source .venv/bin/activate",
            "  pip install -r requirements.txt",
            "  pip install -e .",
        ]
    )


def main(argv: Optional[list[str]] = None) -> int:
    try:
        from discogs_player.cli.commands import app
    except ModuleNotFoundError as exc:
        module_name = exc.name or "unknown"
        print(_missing_dependency_message(module_name), file=sys.stderr)
        return 1

    app_args = argv if argv is not None else sys.argv[1:]
    try:
        app(args=app_args, prog_name="dplayer", standalone_mode=False)
    except SystemExit as exc:
        code = exc.code
        return int(code) if isinstance(code, int) else 1
    except ModuleNotFoundError as exc:
        module_name = exc.name or "unknown"
        print(_missing_dependency_message(module_name), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
