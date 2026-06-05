"""Sync collection use-case boundary."""

from __future__ import annotations

import threading
from typing import Callable

from discogs_player.services.sync_manager import SyncCancelledError, sync_collection

ProgressCallback = Callable[[int, int, int, int], None]

__all__ = ["run_sync_collection", "SyncCancelledError", "ProgressCallback"]


def run_sync_collection(
    *,
    progress_callback: ProgressCallback | None = None,
    allow_empty_deactivate: bool = False,
    cancel_token: threading.Event | None = None,
) -> dict[str, object]:
    return sync_collection(
        progress_callback=progress_callback,
        allow_empty_deactivate=allow_empty_deactivate,
        cancel_token=cancel_token,
    )
