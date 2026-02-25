"""First-time setup readiness report for CLI/UI onboarding."""

from __future__ import annotations

import os

from discogs_player.capabilities import get_capabilities
from discogs_player.core.settings import (
    DISCOGS_TOKEN_ENV,
    get_discogs_token,
    get_setting,
)
from discogs_player.data.db import get_connection
from discogs_player.data.repo import get_release_counts

_DEFAULT_SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8765/callback"
_DISCOGS_TOKEN_URL = "https://www.discogs.com/settings/developers"
_SPOTIFY_DASHBOARD_URL = "https://developer.spotify.com/dashboard"
_SPOTIFY_OAUTH_GUIDE_URL = (
    "https://developer.spotify.com/documentation/web-api/tutorials/code-flow"
)


def _discogs_token_source(conn=None) -> str:
    token = get_discogs_token(conn=conn)
    if not token:
        return "missing"

    env_value = str(os.environ.get(DISCOGS_TOKEN_ENV) or "").strip()
    if env_value:
        return "environment"

    stored_value = str(get_setting("discogs_token", conn=conn) or "").strip()
    if stored_value:
        return "app_settings"

    return "environment"


def run_setup_report() -> dict[str, object]:
    """Return onboarding/setup readiness for Discogs core + optional Spotify."""
    capabilities = get_capabilities().spotify
    conn = get_connection()
    try:
        counts = get_release_counts(conn)
        last_sync_time = get_setting("last_sync_time", conn=conn)
        discogs_source = _discogs_token_source(conn=conn)
    finally:
        conn.close()

    release_count_active = int(counts.get("release_count_active") or 0)
    release_count_total = int(counts.get("release_count_total") or 0)
    discogs_configured = discogs_source != "missing"
    profile = "plus" if capabilities.addon_available else "core"

    if not discogs_configured:
        onboarding_stage = "needs_discogs_token"
    elif release_count_active <= 0:
        onboarding_stage = "needs_initial_sync"
    elif capabilities.addon_available and not capabilities.configured:
        onboarding_stage = "needs_spotify_auth"
    elif not capabilities.addon_available:
        onboarding_stage = "core_ready"
    else:
        onboarding_stage = "ready"

    next_steps: list[str] = []
    if not discogs_configured:
        next_steps.append(f"Discogs token page: {_DISCOGS_TOKEN_URL}")
        next_steps.append('export DISCOGS_TOKEN="your_discogs_personal_token"')
    if release_count_active <= 0:
        next_steps.append("dplayer sync")
    if not capabilities.addon_available:
        next_steps.append('pip install -e ".[spotify]"')
    elif not capabilities.configured:
        next_steps.append(f"Spotify dashboard: {_SPOTIFY_DASHBOARD_URL}")
        next_steps.append(f"Spotify OAuth guide: {_SPOTIFY_OAUTH_GUIDE_URL}")
        next_steps.append(
            f"Spotify Dashboard: add Redirect URI `{_DEFAULT_SPOTIFY_REDIRECT_URI}`"
        )
        next_steps.append("dplayer auth spotify-doctor")
        next_steps.append(
            "dplayer auth spotify --open-browser --listen-host 127.0.0.1 --listen-port 8765"
        )
    else:
        next_steps.append("dplayer devices --json")
        next_steps.append("./scripts/spotify_live_smoke.sh")

    discogs_message = "Discogs token configured."
    if not discogs_configured:
        discogs_message = (
            "Discogs token missing. Set DISCOGS_TOKEN or run "
            "`dplayer config set discogs_token <token>`."
        )

    spotify_next_action = "Optional: install plus profile for Spotify features."
    if capabilities.addon_available and not capabilities.configured:
        spotify_next_action = (
            "Run `dplayer auth spotify-doctor`, then `dplayer auth spotify --open-browser`."
        )
    elif capabilities.addon_available and capabilities.configured:
        spotify_next_action = "Run `dplayer devices --json` to verify connectivity."

    return {
        "profile": profile,
        "onboarding_stage": onboarding_stage,
        "discogs": {
            "configured": bool(discogs_configured),
            "token_source": discogs_source,
            "status_message": discogs_message,
            "token_setup_url": _DISCOGS_TOKEN_URL,
        },
        "collection": {
            "release_count_total": release_count_total,
            "release_count_active": release_count_active,
            "last_sync_time": last_sync_time,
        },
        "spotify": {
            "addon_available": capabilities.addon_available,
            "configured": capabilities.configured,
            "action_label": capabilities.action_label,
            "status_message": capabilities.status_message,
            "next_action": spotify_next_action,
            "dashboard_url": _SPOTIFY_DASHBOARD_URL,
            "oauth_guide_url": _SPOTIFY_OAUTH_GUIDE_URL,
            "redirect_uri": _DEFAULT_SPOTIFY_REDIRECT_URI,
        },
        "links": {
            "discogs_token_url": _DISCOGS_TOKEN_URL,
            "spotify_dashboard_url": _SPOTIFY_DASHBOARD_URL,
            "spotify_oauth_guide_url": _SPOTIFY_OAUTH_GUIDE_URL,
        },
        "next_steps": next_steps,
    }
