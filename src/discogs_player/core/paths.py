"""Filesystem path helpers for XDG-compatible app locations."""

from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "discogs_player"


def _xdg_or_default(env_var: str, default: Path) -> Path:
    return Path(os.environ.get(env_var, default))


def config_dir() -> Path:
    return _xdg_or_default("XDG_CONFIG_HOME", Path.home() / ".config") / APP_NAME


def data_dir() -> Path:
    return _xdg_or_default("XDG_DATA_HOME", Path.home() / ".local" / "share") / APP_NAME


def cache_dir() -> Path:
    return _xdg_or_default("XDG_CACHE_HOME", Path.home() / ".cache") / APP_NAME


def cover_cache_dir() -> Path:
    return cache_dir() / "covers"


def app_settings_path() -> Path:
    return config_dir() / "app_settings.json"


def db_path() -> Path:
    return data_dir() / "app.db"


def ensure_runtime_dirs() -> None:
    config_dir().mkdir(parents=True, exist_ok=True)
    data_dir().mkdir(parents=True, exist_ok=True)
    cache_dir().mkdir(parents=True, exist_ok=True)
