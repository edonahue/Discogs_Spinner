"""Shared CLI render helpers (placeholder module for future expansion)."""

from __future__ import annotations

import json
import sys
from typing import Any

from rich.console import Console

console = Console()


def print_json(payload: Any) -> None:
    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True))
    sys.stdout.write("\n")
