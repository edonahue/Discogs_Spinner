"""Use-cases for CLI config show/set/unset."""

from __future__ import annotations

from discogs_player.core.settings import list_settings, set_setting
from discogs_player.data.db import get_connection


def _normalize_key(raw: str) -> str:
    key = raw.strip()
    if not key:
        raise ValueError("Config key cannot be empty.")
    if any(ch.isspace() for ch in key):
        raise ValueError("Config key cannot contain whitespace.")
    return key


def run_config_show() -> dict[str, str]:
    conn = get_connection()
    try:
        return list_settings(conn=conn)
    finally:
        conn.close()


def run_config_set(key: str, value: str) -> dict[str, str]:
    normalized_key = _normalize_key(key)

    conn = get_connection()
    try:
        set_setting(normalized_key, value, conn=conn)
    finally:
        conn.close()

    return {"key": normalized_key, "value": value}


def run_config_unset(key: str) -> dict[str, object]:
    normalized_key = _normalize_key(key)

    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT 1 FROM app_settings WHERE key = ?",
            (normalized_key,),
        ).fetchone()
        removed = existing is not None
        set_setting(normalized_key, None, conn=conn)
    finally:
        conn.close()

    return {"key": normalized_key, "removed": removed}
