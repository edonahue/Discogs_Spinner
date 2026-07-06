"""Shared CLI render helpers (placeholder module for future expansion)."""

from __future__ import annotations

import json
import sys
from typing import Any

from rich.console import Console

from discogs_player.brand import DISCOGS_ATTRIBUTION, DISCOGS_ATTRIBUTION_TEXT

console = Console()


def with_discogs_attribution(payload: dict[str, Any]) -> dict[str, Any]:
    return {**payload, "attribution": DISCOGS_ATTRIBUTION}


def print_discogs_attribution() -> None:
    console.print(f"{DISCOGS_ATTRIBUTION_TEXT}: {DISCOGS_ATTRIBUTION['url']}")


def print_json(payload: Any) -> None:
    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True))
    sys.stdout.write("\n")
