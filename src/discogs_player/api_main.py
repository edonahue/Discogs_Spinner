"""API server entrypoint."""

from __future__ import annotations

import sys


def _missing_dependency_message(module_name: str) -> str:
    return "\n".join(
        [
            f"Missing API dependency: {module_name}",
            "",
            "Install API profile dependencies:",
            "  pip install -e \".[web]\"",
        ]
    )


def main() -> int:
    try:
        import uvicorn
        from discogs_player_api.app import create_app
    except ModuleNotFoundError as exc:
        module_name = exc.name or "unknown"
        print(_missing_dependency_message(module_name), file=sys.stderr)
        return 1

    print("Spinner for Discogs API — http://127.0.0.1:8768  (Ctrl+C to stop)")
    app = create_app()
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8768,
        log_level="info",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
