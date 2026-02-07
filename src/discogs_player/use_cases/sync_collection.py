"""Sync collection use-case boundary."""

from __future__ import annotations

from typing import Callable

from discogs_player.services.sync_manager import sync_collection

ProgressCallback = Callable[[int, int, int, int], None]


def run_sync_collection(*, progress_callback: ProgressCallback | None = None) -> dict[str, object]:
    return sync_collection(progress_callback=progress_callback)
