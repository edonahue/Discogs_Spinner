"""Filesystem path helpers — cross-platform via platformdirs."""

from __future__ import annotations

from pathlib import Path

from platformdirs import PlatformDirs

_dirs = PlatformDirs(appname="discogs_player", appauthor="discogs_spinner")

APP_NAME = "discogs_player"


def config_dir() -> Path:
    return Path(_dirs.user_config_dir)


def data_dir() -> Path:
    return Path(_dirs.user_data_dir)


def cache_dir() -> Path:
    return Path(_dirs.user_cache_dir)


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
