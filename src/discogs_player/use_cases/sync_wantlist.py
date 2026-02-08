"""Sync wantlist use-case boundary."""

from __future__ import annotations

from typing import Callable

from discogs_player.services.sync_manager import sync_wantlist

ProgressCallback = Callable[[int, int, int, int], None]


def run_sync_wantlist(
    *,
    progress_callback: ProgressCallback | None = None,
    allow_empty_deactivate: bool = False,
) -> dict[str, object]:
    return sync_wantlist(
        progress_callback=progress_callback,
        allow_empty_deactivate=allow_empty_deactivate,
    )
