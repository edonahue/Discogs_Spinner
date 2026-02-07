"""Settings helpers backed by env vars and SQLite app_settings."""

from __future__ import annotations

import os
from typing import Optional

from discogs_player.data.db import get_connection

DISCOGS_TOKEN_ENV = "DISCOGS_TOKEN"


def _load_dotenv_if_available() -> None:
    try:
        from dotenv import load_dotenv
    except ModuleNotFoundError:
        return
    load_dotenv()


def get_discogs_token(conn=None) -> Optional[str]:
    _load_dotenv_if_available()
    env_value = os.environ.get(DISCOGS_TOKEN_ENV)
    if env_value:
        return env_value
    return get_setting("discogs_token", conn=conn)


def get_setting(key: str, default: Optional[str] = None, conn=None) -> Optional[str]:
    owns_conn = conn is None
    if owns_conn:
        conn = get_connection()

    try:
        row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
        if row is None:
            return default
        return row["value"]
    finally:
        if owns_conn:
            conn.close()


def set_setting(key: str, value: Optional[str], conn=None) -> None:
    owns_conn = conn is None
    if owns_conn:
        conn = get_connection()

    try:
        if value is None:
            conn.execute("DELETE FROM app_settings WHERE key = ?", (key,))
        else:
            conn.execute(
                """
                INSERT INTO app_settings(key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )
        conn.commit()
    finally:
        if owns_conn:
            conn.close()


def list_settings(conn=None) -> dict[str, str]:
    owns_conn = conn is None
    if owns_conn:
        conn = get_connection()

    try:
        rows = conn.execute("SELECT key, value FROM app_settings ORDER BY key").fetchall()
        return {str(row["key"]): str(row["value"]) for row in rows}
    finally:
        if owns_conn:
            conn.close()


def get_int_setting(key: str, default: int | None = None, conn=None) -> int | None:
    raw = get_setting(key, conn=conn)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default
