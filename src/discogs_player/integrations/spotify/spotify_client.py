"""Spotify Web API client for playback and device management."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
import random
import time
from typing import Any, Callable

from discogs_player.integrations.spotify.oauth import (
    SpotifyAuthError,
    SpotifyDependencyError,
)

SPOTIFY_API_BASE = "https://api.spotify.com"
DEFAULT_RATE_LIMIT_MAX_RETRIES = 1
DEFAULT_RATE_LIMIT_BACKOFF_SECONDS = 1.0
DEFAULT_RATE_LIMIT_MAX_SLEEP_SECONDS = 15.0
DEFAULT_RATE_LIMIT_JITTER_SECONDS = 0.25
DEFAULT_RATE_LIMIT_RETRY_AFTER_CAP_SECONDS = 15.0


class SpotifyApiError(Exception):
    """Raised when Spotify API returns an error response."""


class SpotifyRateLimitError(SpotifyApiError):
    """Raised when Spotify API returns HTTP 429 and retry budget is exhausted."""

    def __init__(
        self,
        message: str,
        *,
        retry_after_seconds: float | None = None,
    ) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class SpotifyPlaybackError(SpotifyApiError):
    """Raised for playback-specific Spotify failures."""


def _httpx() -> Any:
    try:
        import httpx
    except ModuleNotFoundError as exc:
        raise SpotifyDependencyError(
            "Missing Python dependency: httpx. Install with `pip install -r requirements.txt`."
        ) from exc
    return httpx


def _env_int(name: str, default: int, *, minimum: int = 0) -> int:
    raw = str(os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(minimum, value)


def _env_float(name: str, default: float, *, minimum: float = 0.0) -> float:
    raw = str(os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return max(minimum, value)


def _retry_after_seconds(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = float(text)
    except ValueError:
        return None
    if parsed < 0:
        return None
    return parsed


@dataclass
class SpotifyClient:
    access_token: str
    timeout_seconds: float = 30.0
    rate_limit_max_retries: int = _env_int(
        "DP_SPOTIFY_API_MAX_RETRIES",
        DEFAULT_RATE_LIMIT_MAX_RETRIES,
        minimum=0,
    )
    rate_limit_backoff_seconds: float = _env_float(
        "DP_SPOTIFY_API_BACKOFF_SECONDS",
        DEFAULT_RATE_LIMIT_BACKOFF_SECONDS,
        minimum=0.0,
    )
    rate_limit_max_sleep_seconds: float = _env_float(
        "DP_SPOTIFY_API_MAX_SLEEP_SECONDS",
        DEFAULT_RATE_LIMIT_MAX_SLEEP_SECONDS,
        minimum=0.0,
    )
    rate_limit_jitter_seconds: float = _env_float(
        "DP_SPOTIFY_API_JITTER_SECONDS",
        DEFAULT_RATE_LIMIT_JITTER_SECONDS,
        minimum=0.0,
    )
    rate_limit_retry_after_cap_seconds: float = _env_float(
        "DP_SPOTIFY_API_RETRY_AFTER_CAP_SECONDS",
        DEFAULT_RATE_LIMIT_RETRY_AFTER_CAP_SECONDS,
        minimum=0.0,
    )
    playback_rate_limit_max_retries: int = _env_int(
        "DP_SPOTIFY_PLAYBACK_API_MAX_RETRIES",
        1,
        minimum=0,
    )
    # Optional callable that refreshes the access token and returns the new value.
    # When provided, a single 401/403 triggers one silent refresh-and-retry before
    # raising SpotifyAuthError to the caller.
    token_refresher: Callable[[], str] | None = field(default=None, repr=False)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, object] | None = None,
        json_body: dict[str, object] | None = None,
        expected_statuses: set[int] | None = None,
        max_retries: int | None = None,
    ) -> Any:
        httpx_module = _httpx()
        url = f"{SPOTIFY_API_BASE}{path}"
        retry_budget = (
            int(self.rate_limit_max_retries)
            if max_retries is None
            else int(max_retries)
        )
        retry_budget = max(0, retry_budget)
        _auth_refreshed = False
        attempt = 0
        while attempt <= retry_budget:
            try:
                response = httpx_module.request(
                    method,
                    url,
                    headers=self._headers(),
                    params=params,
                    json=json_body,
                    timeout=self.timeout_seconds,
                )
            except Exception as exc:
                if isinstance(exc, httpx_module.RequestError):
                    raise SpotifyApiError(f"Spotify request failed: {exc}") from exc
                raise

            if response.status_code in (401, 403):
                if self.token_refresher is not None and not _auth_refreshed:
                    _auth_refreshed = True
                    try:
                        self.access_token = self.token_refresher()
                    except Exception:
                        raise SpotifyAuthError(
                            "Spotify auth failed. Re-authenticate or provide a valid access token."
                        )
                    continue  # retry same attempt with refreshed token
                raise SpotifyAuthError(
                    "Spotify auth failed. Re-authenticate or provide a valid access token."
                )

            # Rate-limit handling:
            # - honor explicit Retry-After from Spotify
            # - use bounded exponential backoff only when header is absent
            retry_after_header = _retry_after_seconds(response.headers.get("Retry-After"))
            retry_after = retry_after_header
            if retry_after is not None:
                retry_after_cap = float(self.rate_limit_retry_after_cap_seconds)
                if retry_after_cap > 0:
                    retry_after = min(retry_after, retry_after_cap)
                elif float(self.rate_limit_max_sleep_seconds) > 0:
                    # Even when no explicit cap is configured, never block for
                    # multi-hour Retry-After windows in one request path.
                    retry_after = min(
                        retry_after,
                        float(self.rate_limit_max_sleep_seconds),
                    )
            if response.status_code == 429 and attempt < retry_budget:
                if retry_after is None:
                    retry_after = float(self.rate_limit_backoff_seconds) * (2**attempt)
                    if self.rate_limit_jitter_seconds > 0:
                        retry_after += random.uniform(0.0, self.rate_limit_jitter_seconds)
                    retry_after = min(float(self.rate_limit_max_sleep_seconds), retry_after)
                if retry_after > 0:
                    time.sleep(retry_after)
                attempt += 1
                continue

            allowed = expected_statuses or {200}
            if response.status_code == 429:
                detail = response.text[:240] or "Too many requests"
                if retry_after_header is None:
                    raise SpotifyRateLimitError(
                        f"Spotify API request failed (429): {detail}"
                    )
                retry_after_for_error = (
                    retry_after if retry_after is not None else retry_after_header
                )
                if retry_after_for_error != retry_after_header:
                    raise SpotifyRateLimitError(
                        f"Spotify API request failed (429): {detail} "
                        f"(retry_after={retry_after_for_error:.3f}s, "
                        f"header_retry_after={retry_after_header:.3f}s)",
                        retry_after_seconds=retry_after_for_error,
                    )
                raise SpotifyRateLimitError(
                    f"Spotify API request failed (429): {detail} "
                    f"(retry_after={retry_after_for_error:.3f}s)",
                    retry_after_seconds=retry_after_for_error,
                )
            if response.status_code not in allowed:
                detail = response.text[:240]
                raise SpotifyApiError(
                    f"Spotify API request failed ({response.status_code}): {detail}"
                )

            if not response.content:
                return None

            try:
                return response.json()
            except ValueError as exc:
                raise SpotifyApiError("Spotify API response was not valid JSON") from exc

        raise SpotifyRateLimitError("Spotify API request failed (429): Too many requests")

    def list_devices(self) -> list[dict[str, object]]:
        payload = self._request(
            "GET",
            "/v1/me/player/devices",
            max_retries=self.playback_rate_limit_max_retries,
        )
        devices = payload.get("devices") if isinstance(payload, dict) else []
        if not isinstance(devices, list):
            return []

        result: list[dict[str, object]] = []
        for raw in devices:
            if not isinstance(raw, dict):
                continue
            result.append(
                {
                    "id": raw.get("id"),
                    "name": raw.get("name"),
                    "type": raw.get("type"),
                    "is_active": bool(raw.get("is_active")),
                    "is_restricted": bool(raw.get("is_restricted")),
                    "volume_percent": raw.get("volume_percent"),
                }
            )
        return result

    def search_albums(self, *, query: str, limit: int = 10) -> list[dict[str, object]]:
        payload = self._request(
            "GET",
            "/v1/search",
            params={
                "q": query,
                "type": "album",
                "limit": max(1, min(50, int(limit))),
            },
        )
        albums = payload.get("albums", {}) if isinstance(payload, dict) else {}
        items = albums.get("items") if isinstance(albums, dict) else []
        if not isinstance(items, list):
            return []

        result: list[dict[str, object]] = []
        for raw in items:
            if not isinstance(raw, dict):
                continue

            artists_raw = raw.get("artists")
            artist_names: list[str] = []
            if isinstance(artists_raw, list):
                for artist in artists_raw:
                    if isinstance(artist, dict) and artist.get("name"):
                        artist_names.append(str(artist["name"]))

            external_urls = (
                raw.get("external_urls")
                if isinstance(raw.get("external_urls"), dict)
                else {}
            )
            result.append(
                {
                    "id": raw.get("id"),
                    "name": raw.get("name"),
                    "artists": artist_names,
                    "release_date": raw.get("release_date"),
                    "album_type": raw.get("album_type"),
                    "album_group": raw.get("album_group"),
                    "total_tracks": raw.get("total_tracks"),
                    "uri": raw.get("uri"),
                    "external_url": external_urls.get("spotify")
                    if isinstance(external_urls, dict)
                    else None,
                }
            )
        return result

    def start_album_playback(
        self, spotify_album_id: str, *, device_id: str | None = None
    ) -> None:
        album_id = spotify_album_id.removeprefix("spotify:album:")
        context_uri = f"spotify:album:{album_id}"
        params: dict[str, object] | None = {"device_id": device_id} if device_id else None

        try:
            self._request(
                "PUT",
                "/v1/me/player/play",
                params=params,
                json_body={"context_uri": context_uri},
                expected_statuses={204},
                max_retries=self.playback_rate_limit_max_retries,
            )
        except SpotifyApiError as exc:
            raise SpotifyPlaybackError(str(exc)) from exc
