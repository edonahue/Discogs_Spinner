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
from discogs_player.integrations.provider_registry import (
    experimental_flag,
    get_backend,
    get_backend_type,
    is_provider_enabled,
    listed_provider_ids,
    provider_metadata,
    registered_provider_ids,
)

__all__ = [
    "NullPlayerBackend",
    "PlayerApiError",
    "PlayerAuthError",
    "PlayerBackend",
    "PlayerBackendError",
    "PlayerDependencyError",
    "PlayerPlaybackError",
    "get_backend",
    "get_backend_type",
    "experimental_flag",
    "is_provider_enabled",
    "listed_provider_ids",
    "provider_metadata",
    "registered_provider_ids",
]
