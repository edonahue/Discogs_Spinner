"""Shared CLI render helpers (placeholder module for future expansion)."""

from __future__ import annotations

import json
from typing import Any

from rich.console import Console

console = Console()


def print_json(payload: Any) -> None:
    console.print(json.dumps(payload, indent=2, sort_keys=True))

