"""Redacted diagnostics bundle for support and issue reporting."""

from __future__ import annotations

import os
import platform
import sys
from importlib.metadata import PackageNotFoundError, version

from discogs_player.capabilities import get_capabilities, get_player_backend
from discogs_player.core.paths import cache_dir, config_dir, data_dir, db_path
from discogs_player.core.settings import list_settings
from discogs_player.use_cases.setup_report import run_setup_report
from discogs_player.use_cases.status_report import get_status_report

_TRACKED_ENV_VARS = (
    "DISCOGS_TOKEN",
    "SPOTIFY_ACCESS_TOKEN",
    "SPOTIFY_REFRESH_TOKEN",
    "SPOTIFY_CLIENT_ID",
    "SPOTIFY_SECRET",
    "SPOTIFY_CLIENT_SECRET",
)


def _app_version() -> str:
    try:
        return version("discogs_player")
    except PackageNotFoundError:
        return "unknown"


def _settings_presence_snapshot() -> dict[str, dict[str, object]]:
    settings = list_settings()
    snapshot: dict[str, dict[str, object]] = {}
    for key, raw_value in sorted(settings.items()):
        value = str(raw_value or "").strip()
        snapshot[key] = {
            "present": bool(value),
            "redacted": True,
        }
    return snapshot


def _env_presence_snapshot() -> dict[str, bool]:
    return {
        key: bool(str(os.environ.get(key) or "").strip())
        for key in _TRACKED_ENV_VARS
    }


def run_diagnostics_report() -> dict[str, object]:
    """Build a redacted diagnostics payload safe for issue reports."""
    capabilities = get_capabilities()
    spotify_capabilities = capabilities.spotify
    backend = get_player_backend()
    status_payload = get_status_report()
    setup_payload = run_setup_report()

    provider_diagnostics: dict[str, object]
    try:
        provider_diagnostics = backend.auth_diagnostics()
    except Exception as exc:
        provider_diagnostics = {
            "backend": backend.name,
            "diagnosis": "error",
            "status_message": str(exc),
        }

    providers_payload: list[dict[str, object]] = []
    for provider in getattr(capabilities, "providers", ()):
        providers_payload.append(
            {
                "provider_id": provider.provider_id,
                "display_name": provider.display_name,
                "listed": provider.listed,
                "enabled": provider.enabled,
                "importable": provider.importable,
                "addon_available": provider.addon_available,
                "configured": provider.configured,
                "action_label": provider.action_label,
                "status_message": provider.status_message,
                "docs_url": provider.docs_url,
                "experimental": provider.experimental,
                "experimental_flag": provider.experimental_flag,
            }
        )

    return {
        "app": {
            "name": "discogs_player",
            "version": _app_version(),
        },
        "runtime": {
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
        },
        "paths": {
            "config_dir": str(config_dir()),
            "data_dir": str(data_dir()),
            "cache_dir": str(cache_dir()),
            "db_path": str(db_path()),
            "db_exists": db_path().exists(),
        },
        "env_presence": _env_presence_snapshot(),
        "settings_presence": _settings_presence_snapshot(),
        "capabilities": {
            "spotify": {
                "addon_available": spotify_capabilities.addon_available,
                "configured": spotify_capabilities.configured,
                "action_label": spotify_capabilities.action_label,
                "status_message": spotify_capabilities.status_message,
            },
            "providers": providers_payload,
        },
        "provider_readiness": dict(status_payload.get("provider_readiness") or {}),
        "legacy_spotify_compatibility": {
            "status_report_has_spotify_capability": isinstance(
                status_payload.get("spotify_capability"), dict
            ),
            "setup_report_has_spotify_block": isinstance(
                setup_payload.get("spotify"), dict
            ),
        },
        "status_report": status_payload,
        "setup_report": setup_payload,
        "provider_diagnostics": {
            backend.name: provider_diagnostics,
        },
        "command_hint": "dplayer diagnostics --json",
    }
