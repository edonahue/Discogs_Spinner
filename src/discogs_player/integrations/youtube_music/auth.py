"""YouTube Music auth helpers (v1: unauthenticated — no configuration needed)."""

from __future__ import annotations

import importlib.util


def has_youtube_music_configuration() -> bool:
    """v1 uses unauthenticated search — always considered configured."""
    return True


def get_youtube_music_auth_diagnostics() -> dict[str, object]:
    """Return version and status info for YouTube Music backend."""
    addon_available = importlib.util.find_spec("ytmusicapi") is not None
    return {
        "backend": "youtube_music",
        "addon_available": addon_available,
        "configured": True,
        "note": "v1 uses unauthenticated search — no credentials required",
    }
