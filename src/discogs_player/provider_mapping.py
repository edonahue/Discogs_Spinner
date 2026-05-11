"""Provider-neutral mapping field compatibility helpers."""

from __future__ import annotations

from typing import Any

_SPOTIFY_PROVIDER_ID = "spotify"


def _provider_id_for_mapping(
    *,
    existing_provider_id: object | None,
    spotify_album_id: object | None,
) -> str | None:
    if isinstance(existing_provider_id, str):
        value = existing_provider_id.strip()
        if value:
            return value
    if isinstance(spotify_album_id, str) and spotify_album_id.strip():
        return _SPOTIFY_PROVIDER_ID
    return None


def with_provider_mapping_aliases(value: Any) -> Any:
    """Return a copy of ``value`` with provider-neutral mapping aliases attached.

    Compatibility behavior:
    - If ``spotify_album_id`` exists in a dict, add ``provider_release_id`` when missing.
    - If ``spotify_album_id`` exists in a dict, add ``provider_id`` when missing
      (defaults to ``spotify`` when a mapping is present).
    - Recurses through nested dict/list payloads.
    """

    if isinstance(value, list):
        return [with_provider_mapping_aliases(item) for item in value]
    if not isinstance(value, dict):
        return value

    out: dict[str, Any] = {
        key: with_provider_mapping_aliases(item) for key, item in value.items()
    }

    if "spotify_album_id" in out:
        if "provider_release_id" not in out:
            out["provider_release_id"] = out.get("spotify_album_id")
        if "provider_id" not in out:
            out["provider_id"] = _provider_id_for_mapping(
                existing_provider_id=None,
                spotify_album_id=out.get("spotify_album_id"),
            )

    return out

