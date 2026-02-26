"""Registry helpers for optional streaming backend providers."""

from __future__ import annotations

import os
from importlib import import_module

from discogs_player.integrations.null_backend import NullPlayerBackend
from discogs_player.integrations.player_backend import PlayerBackend

# Provider-id -> (module path, backend class name)
_BACKEND_SPECS: dict[str, tuple[str, str]] = {
    "spotify": ("discogs_player.integrations.spotify.backend", "SpotifyPlayerBackend"),
    "youtube_music": (
        "discogs_player.integrations.youtube_music.backend",
        "YouTubeMusicPlayerBackend",
    ),
}

_PROVIDER_DISPLAY_NAMES: dict[str, str] = {
    "spotify": "Spotify",
    "youtube_music": "YouTube Music",
}

_PROVIDER_DOCS_URLS: dict[str, str] = {
    "spotify": "https://developer.spotify.com/documentation/web-api",
    "youtube_music": "https://music.youtube.com/",
}

_EXPERIMENTAL_PROVIDER_FLAGS: dict[str, str] = {
    "youtube_music": "DP_ENABLE_EXPERIMENTAL_YOUTUBE_MUSIC",
}


def _env_flag_enabled(env_key: str) -> bool:
    raw = str(os.environ.get(env_key) or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def experimental_flag(provider_id: str) -> str | None:
    return _EXPERIMENTAL_PROVIDER_FLAGS.get(provider_id)


def is_provider_enabled(provider_id: str) -> bool:
    flag = experimental_flag(provider_id)
    if not flag:
        return True
    return _env_flag_enabled(flag)


def listed_provider_ids() -> tuple[str, ...]:
    """Return all listed providers, including disabled experimental stubs."""
    return tuple(_BACKEND_SPECS.keys())


def registered_provider_ids(*, include_disabled_experimental: bool = False) -> tuple[str, ...]:
    """Return enabled provider ids in stable registration order."""
    ids: list[str] = []
    for provider_id in _BACKEND_SPECS:
        if include_disabled_experimental or is_provider_enabled(provider_id):
            ids.append(provider_id)
    return tuple(ids)


def provider_metadata(provider_id: str) -> dict[str, object] | None:
    """Return metadata for one listed provider id."""
    if provider_id not in _BACKEND_SPECS:
        return None
    flag = experimental_flag(provider_id)
    return {
        "provider_id": provider_id,
        "display_name": _PROVIDER_DISPLAY_NAMES.get(provider_id, provider_id),
        "docs_url": _PROVIDER_DOCS_URLS.get(provider_id),
        "experimental": bool(flag),
        "experimental_flag": flag,
        "enabled": is_provider_enabled(provider_id),
    }


def get_backend_type(provider_id: str) -> type[PlayerBackend] | None:
    """Resolve a backend class for one provider id, if importable."""
    spec = _BACKEND_SPECS.get(provider_id)
    if spec is None:
        return None
    if not is_provider_enabled(provider_id):
        return None

    module_path, class_name = spec
    try:
        module = import_module(module_path)
    except ModuleNotFoundError as exc:
        missing = str(exc.name or "")
        module_prefix = module_path.rsplit(".", 1)[0]
        if missing.startswith(module_prefix):
            return None
        raise

    backend_cls = getattr(module, class_name, None)
    if not isinstance(backend_cls, type):
        return None
    if not issubclass(backend_cls, PlayerBackend):
        return None
    return backend_cls


def get_backend(provider_id: str) -> PlayerBackend:
    """Instantiate one provider backend with Null fallback."""
    backend_cls = get_backend_type(provider_id)
    if backend_cls is None:
        return NullPlayerBackend()

    backend = backend_cls()
    if not backend.addon_available():
        return NullPlayerBackend()
    return backend
