"""Integration backends and optional addon adapters."""

from discogs_player.integrations.null_backend import NullPlayerBackend
from discogs_player.integrations.player_backend import (
    PlayerApiError,
    PlayerAuthError,
    PlayerBackend,
    PlayerBackendError,
    PlayerDependencyError,
    PlayerPlaybackError,
)

__all__ = [
    "NullPlayerBackend",
    "PlayerApiError",
    "PlayerAuthError",
    "PlayerBackend",
    "PlayerBackendError",
    "PlayerDependencyError",
    "PlayerPlaybackError",
]
