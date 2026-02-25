"""Use-cases for CLI config show/set/unset."""

from __future__ import annotations

from discogs_player.core.settings import DISCOGS_TOKEN_ENV, list_settings, set_setting
from discogs_player.data.db import get_connection

_CANONICAL_DISCOGS_TOKEN_KEY = "discogs_token"
_DISCOGS_TOKEN_KEY_ALIASES: tuple[str, ...] = (
    _CANONICAL_DISCOGS_TOKEN_KEY,
    DISCOGS_TOKEN_ENV,
)


def _normalize_key(raw: str) -> str:
    key = raw.strip()
    if not key:
        raise ValueError("Config key cannot be empty.")
    if any(ch.isspace() for ch in key):
        raise ValueError("Config key cannot contain whitespace.")
    if key.casefold() == _CANONICAL_DISCOGS_TOKEN_KEY:
        return _CANONICAL_DISCOGS_TOKEN_KEY
    return key


def run_config_show() -> dict[str, str]:
    conn = get_connection()
    try:
        return list_settings(conn=conn)
    finally:
        conn.close()


def run_config_set(key: str, value: str) -> dict[str, str]:
    normalized_key = _normalize_key(key)
    normalized_value = value
    if normalized_key == _CANONICAL_DISCOGS_TOKEN_KEY:
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError("Discogs token cannot be empty.")

    conn = get_connection()
    try:
        if normalized_key == _CANONICAL_DISCOGS_TOKEN_KEY:
            for alias in _DISCOGS_TOKEN_KEY_ALIASES:
                if alias == _CANONICAL_DISCOGS_TOKEN_KEY:
                    continue
                set_setting(alias, None, conn=conn)
        set_setting(normalized_key, normalized_value, conn=conn)
    finally:
        conn.close()

    return {"key": normalized_key, "value": normalized_value}


def run_config_unset(key: str) -> dict[str, object]:
    normalized_key = _normalize_key(key)
    keys_to_unset = (
        _DISCOGS_TOKEN_KEY_ALIASES
        if normalized_key == _CANONICAL_DISCOGS_TOKEN_KEY
        else (normalized_key,)
    )

    conn = get_connection()
    try:
        placeholders = ", ".join(["?"] * len(keys_to_unset))
        rows = conn.execute(
            f"SELECT key FROM app_settings WHERE key IN ({placeholders})",
            keys_to_unset,
        ).fetchall()
        removed = bool(rows)
        for key_name in keys_to_unset:
            set_setting(key_name, None, conn=conn)
    finally:
        conn.close()

    return {"key": normalized_key, "removed": removed}
