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
from discogs_player.use_cases.provider_readiness import (
    build_provider_readiness_contract,
)

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

    # Token was found by get_discogs_token() but not under the env var or the
    # canonical "discogs_token" key — must be under an alias key in app_settings.
    return "app_settings"


def run_setup_report() -> dict[str, object]:
    """Return onboarding/setup readiness for Discogs core + optional Spotify."""
    app_capabilities = get_capabilities()
    capabilities = app_capabilities.spotify
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
    collection_synced = bool(release_count_active > 0)
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
    first_run_actions: list[str] = []
    daily_use_actions: list[str] = []
    if not discogs_configured:
        first_run_actions.extend(
            [
                "Configure Discogs token.",
                "Run `dplayer setup` again to confirm onboarding stage.",
            ]
        )
        next_steps.append(f"Discogs token page: {_DISCOGS_TOKEN_URL}")
        next_steps.append('export DISCOGS_TOKEN="your_discogs_personal_token"')
        daily_use_actions.extend(
            [
                "Add your Discogs token, then rerun setup.",
                "After setup, run first sync to unlock browsing and spin flows.",
            ]
        )
    if release_count_active <= 0:
        first_run_actions.append("Run first Discogs sync.")
        next_steps.append("dplayer sync")
        next_steps.append("dplayer status")
        next_steps.append("dplayer list --limit 10")
        daily_use_actions.append(
            "Run `dplayer sync` and wait for collection import before daily browsing."
        )
    if not capabilities.addon_available:
        first_run_actions.append("Optionally enable Spotify addon.")
        next_steps.append('pip install -e ".[spotify]"')
        daily_use_actions.append(
            "Optional: install Spotify addon later; Discogs browsing and discovery work without it."
        )
    elif not capabilities.configured:
        first_run_actions.extend(
            [
                "Run Spotify diagnostics.",
                "Complete Spotify auth callback flow.",
            ]
        )
        next_steps.append(f"Spotify dashboard: {_SPOTIFY_DASHBOARD_URL}")
        next_steps.append(f"Spotify OAuth guide: {_SPOTIFY_OAUTH_GUIDE_URL}")
        next_steps.append(
            f"Spotify Dashboard: add Redirect URI `{_DEFAULT_SPOTIFY_REDIRECT_URI}`"
        )
        next_steps.append("dplayer auth spotify-doctor")
        next_steps.append(
            "dplayer auth spotify --open-browser --listen-host 127.0.0.1 --listen-port 8765"
        )
        daily_use_actions.append(
            "Optional: connect Spotify after sync to enable direct playback handoff."
        )
    else:
        first_run_actions.extend(
            [
                "Verify Spotify devices.",
                "Run optional playback smoke check.",
            ]
        )
        next_steps.append("dplayer devices --json")
        next_steps.append("./scripts/spotify_live_smoke.sh")
        next_steps.append("dplayer play --last-spin --open")
        daily_use_actions.extend(
            [
                "Run `dplayer spin` to pick something quickly from your collection.",
                "Use `dplayer play --last-spin --open` to hand off the last pick to playback.",
                "Check `dplayer value gems` weekly for overlooked high-signal records.",
            ]
        )

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

    first_run_checklist = {
        "discogs_configured": bool(discogs_configured),
        "collection_synced": collection_synced,
        "spotify_addon_available": bool(capabilities.addon_available),
        "spotify_configured": bool(capabilities.configured),
    }
    first_run_checklist["ready_for_daily_use"] = bool(
        first_run_checklist["discogs_configured"]
        and first_run_checklist["collection_synced"]
        and (
            not first_run_checklist["spotify_addon_available"]
            or first_run_checklist["spotify_configured"]
        )
    )

    readiness_contract = build_provider_readiness_contract(
        app_capabilities=app_capabilities,
        discogs_configured=discogs_configured,
        collection_synced=collection_synced,
    )

    return {
        "profile": profile,
        "onboarding_stage": onboarding_stage,
        "provider_readiness": readiness_contract,
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
        "first_run_checklist": first_run_checklist,
        "first_run_actions": first_run_actions,
        "daily_use_actions": list(dict.fromkeys(daily_use_actions)),
        "next_steps": next_steps,
    }
