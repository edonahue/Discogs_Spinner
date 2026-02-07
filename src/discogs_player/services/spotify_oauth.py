"""Spotify OAuth/token helpers for headless CLI use."""

from __future__ import annotations

import os
import time
from typing import Any

from discogs_player.core.settings import get_setting, set_setting

SPOTIFY_ACCESS_TOKEN_ENV = "SPOTIFY_ACCESS_TOKEN"
SPOTIFY_REFRESH_TOKEN_ENV = "SPOTIFY_REFRESH_TOKEN"
SPOTIFY_CLIENT_ID_ENV = "SPOTIFY_CLIENT_ID"
SPOTIFY_CLIENT_SECRET_ENV = "SPOTIFY_CLIENT_SECRET"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"


class SpotifyOAuthError(Exception):
    """Base class for Spotify OAuth errors."""


class SpotifyDependencyError(SpotifyOAuthError):
    """Raised when required Python dependency for Spotify integration is missing."""


class SpotifyAuthError(SpotifyOAuthError):
    """Raised for missing/invalid Spotify credentials or token refresh failures."""


def _load_dotenv_if_available() -> None:
    try:
        from dotenv import load_dotenv
    except ModuleNotFoundError:
        return
    load_dotenv()


def _httpx() -> Any:
    try:
        import httpx
    except ModuleNotFoundError as exc:
        raise SpotifyDependencyError(
            "Missing Python dependency: httpx. Install with `pip install -r requirements.txt`."
        ) from exc
    return httpx


def _int_or_none(raw: str | None) -> int | None:
    if raw is None:
        return None
    raw = raw.strip()
    if not raw:
        return None
    if not raw.isdigit():
        return None
    return int(raw)


def _refresh_spotify_access_token(
    *,
    refresh_token: str,
    client_id: str,
    client_secret: str,
    timeout_seconds: float = 30.0,
) -> tuple[str, int, str | None]:
    httpx_module = _httpx()

    try:
        response = httpx_module.post(
            SPOTIFY_TOKEN_URL,
            data={"grant_type": "refresh_token", "refresh_token": refresh_token},
            auth=(client_id, client_secret),
            timeout=timeout_seconds,
        )
    except Exception as exc:
        if isinstance(exc, httpx_module.RequestError):
            raise SpotifyAuthError(f"Spotify token refresh request failed: {exc}") from exc
        raise

    if response.status_code >= 400:
        detail = response.text[:240]
        raise SpotifyAuthError(
            f"Spotify token refresh failed ({response.status_code}): {detail}"
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise SpotifyAuthError("Spotify token refresh response was not valid JSON") from exc

    access_token = payload.get("access_token")
    expires_in = payload.get("expires_in")
    returned_refresh_token = payload.get("refresh_token")

    if not isinstance(access_token, str) or not access_token:
        raise SpotifyAuthError("Spotify token refresh did not return access_token")

    expires_value = int(expires_in) if isinstance(expires_in, int) else 3600

    if returned_refresh_token is not None and not isinstance(returned_refresh_token, str):
        returned_refresh_token = None

    return access_token, expires_value, returned_refresh_token


def get_spotify_access_token(conn=None) -> str:
    """Resolve Spotify access token from env, stored settings, or refresh flow."""
    _load_dotenv_if_available()

    env_token = os.environ.get(SPOTIFY_ACCESS_TOKEN_ENV)
    if env_token:
        return env_token.strip()

    stored_token = get_setting("spotify_access_token", conn=conn)
    expires_at_raw = get_setting("spotify_access_token_expires_at", conn=conn)
    expires_at = _int_or_none(expires_at_raw)

    now_epoch = int(time.time())
    if stored_token and (expires_at is None or expires_at > now_epoch + 60):
        return stored_token

    refresh_token = os.environ.get(SPOTIFY_REFRESH_TOKEN_ENV) or get_setting(
        "spotify_refresh_token", conn=conn
    )
    client_id = os.environ.get(SPOTIFY_CLIENT_ID_ENV) or get_setting("spotify_client_id", conn=conn)
    client_secret = os.environ.get(SPOTIFY_CLIENT_SECRET_ENV) or get_setting(
        "spotify_client_secret", conn=conn
    )

    if refresh_token and client_id and client_secret:
        token, expires_in, returned_refresh_token = _refresh_spotify_access_token(
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret,
        )
        set_setting("spotify_access_token", token, conn=conn)
        set_setting("spotify_access_token_expires_at", str(now_epoch + max(1, expires_in)), conn=conn)
        if returned_refresh_token:
            set_setting("spotify_refresh_token", returned_refresh_token, conn=conn)
        return token

    if stored_token:
        return stored_token

    raise SpotifyAuthError(
        "Spotify access token not configured. Set SPOTIFY_ACCESS_TOKEN, or configure "
        "SPOTIFY_CLIENT_ID/SPOTIFY_CLIENT_SECRET/SPOTIFY_REFRESH_TOKEN for auto-refresh."
    )
