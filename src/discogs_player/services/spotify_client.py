"""Spotify Web API client for playback and device management."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from discogs_player.services.spotify_oauth import SpotifyAuthError, SpotifyDependencyError

SPOTIFY_API_BASE = "https://api.spotify.com"


class SpotifyApiError(Exception):
    """Raised when Spotify API returns an error response."""


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


@dataclass
class SpotifyClient:
    access_token: str
    timeout_seconds: float = 30.0

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
    ) -> Any:
        httpx_module = _httpx()
        url = f"{SPOTIFY_API_BASE}{path}"

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
            raise SpotifyAuthError(
                "Spotify auth failed. Re-authenticate or provide a valid access token."
            )

        allowed = expected_statuses or {200}
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

    def list_devices(self) -> list[dict[str, object]]:
        payload = self._request("GET", "/v1/me/player/devices")
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

    def start_album_playback(self, spotify_album_id: str, *, device_id: str | None = None) -> None:
        album_id = spotify_album_id.removeprefix("spotify:album:")
        context_uri = f"spotify:album:{album_id}"
        params = {"device_id": device_id} if device_id else None

        try:
            self._request(
                "PUT",
                "/v1/me/player/play",
                params=params,
                json_body={"context_uri": context_uri},
                expected_statuses={204},
            )
        except SpotifyApiError as exc:
            raise SpotifyPlaybackError(str(exc)) from exc
