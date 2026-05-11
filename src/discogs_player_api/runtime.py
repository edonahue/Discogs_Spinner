"""Route execution helpers."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from discogs_player.provider_mapping import with_provider_mapping_aliases
from discogs_player_api.contracts import success_envelope
from discogs_player_api.errors import raise_http_exception_for

T = TypeVar("T")


def run_use_case(
    call: Callable[[], T],
    *,
    meta: dict[str, object] | None = None,
) -> dict[str, object]:
    try:
        data = call()
    except Exception as exc:  # noqa: BLE001 - centralized API mapping.
        raise_http_exception_for(exc)
    return success_envelope(with_provider_mapping_aliases(data), meta=meta)
