"""Discogs API client for collection sync."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

import httpx


class DiscogsError(Exception):
    """Base class for Discogs client errors."""


class DiscogsAuthError(DiscogsError):
    """Discogs authentication failure."""


class DiscogsApiError(DiscogsError):
    """Discogs API failure."""


ProgressCallback = Callable[[int, int, int, int], None]


@dataclass
class DiscogsClient:
    token: str
    user_agent: str = "discogs_player/0.1"
    timeout_seconds: float = 30.0

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Discogs token={self.token}",
            "User-Agent": self.user_agent,
            "Accept": "application/json",
        }

    def _request_with_backoff(
        self,
        client: httpx.Client,
        method: str,
        path: str,
        *,
        params: dict[str, object] | None = None,
    ) -> httpx.Response:
        url = f"https://api.discogs.com{path}"
        max_attempts = 5

        for attempt in range(1, max_attempts + 1):
            response = client.request(method, url, params=params)
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                sleep_for = int(retry_after) if retry_after and retry_after.isdigit() else attempt
                time.sleep(max(1, sleep_for))
                continue

            if response.status_code in (401, 403):
                raise DiscogsAuthError(
                    "Discogs auth failed. Check DISCOGS_TOKEN and ensure it has collection access."
                )

            if response.status_code >= 500 and attempt < max_attempts:
                time.sleep(attempt)
                continue

            if response.status_code >= 400:
                raise DiscogsApiError(
                    f"Discogs request failed ({response.status_code}): {response.text[:200]}"
                )

            return response

        raise DiscogsApiError("Discogs API retries exhausted due to rate limiting/server errors")

    def _get_username(self, client: httpx.Client) -> str:
        response = self._request_with_backoff(client, "GET", "/oauth/identity")
        payload = response.json()
        username = payload.get("username")
        if not username:
            raise DiscogsApiError("Discogs identity response missing username")
        return str(username)

    def fetch_collection_releases(
        self,
        *,
        per_page: int = 100,
        progress_callback: ProgressCallback | None = None,
    ) -> list[dict[str, object]]:
        releases: list[dict[str, object]] = []

        with httpx.Client(headers=self._headers(), timeout=self.timeout_seconds) as client:
            username = self._get_username(client)
            page = 1
            pages = 1

            while page <= pages:
                response = self._request_with_backoff(
                    client,
                    "GET",
                    f"/users/{username}/collection/folders/0/releases",
                    params={"page": page, "per_page": per_page},
                )
                payload = response.json()
                pagination = payload.get("pagination", {})
                pages = int(pagination.get("pages", 1))
                page_releases = payload.get("releases", [])

                now = datetime.now(timezone.utc).isoformat()
                normalized = [self._normalize_release(item, now) for item in page_releases]
                normalized = [item for item in normalized if item is not None]
                releases.extend(normalized)

                if progress_callback is not None:
                    progress_callback(page, pages, len(normalized), len(releases))

                page += 1

        return releases

    def _normalize_release(
        self,
        item: dict[str, object],
        synced_at: str,
    ) -> dict[str, object] | None:
        basic = item.get("basic_information") if isinstance(item, dict) else None
        if not isinstance(basic, dict):
            return None

        release_id = basic.get("id")
        if not isinstance(release_id, int):
            return None

        artists = basic.get("artists") if isinstance(basic.get("artists"), list) else []
        artist_names = []
        for artist in artists:
            if isinstance(artist, dict) and artist.get("name"):
                artist_names.append(str(artist["name"]))

        title = str(basic.get("title") or "")
        year = basic.get("year")
        year_value = int(year) if isinstance(year, int) else None

        genres = basic.get("genres") if isinstance(basic.get("genres"), list) else []
        styles = basic.get("styles") if isinstance(basic.get("styles"), list) else []

        added_at_raw = item.get("date_added") if isinstance(item, dict) else None
        added_at = str(added_at_raw) if added_at_raw else None

        thumb_url = basic.get("thumb")
        cover_url = basic.get("cover_image")

        return {
            "discogs_release_id": release_id,
            "artist": ", ".join(artist_names) or None,
            "title": title or None,
            "year": year_value,
            "genres": genres,
            "styles": styles,
            "thumb_url": str(thumb_url) if thumb_url else None,
            "cover_url": str(cover_url) if cover_url else None,
            "added_at": added_at,
            "last_synced_at": synced_at,
            "is_active": 1,
        }


def release_to_json(release: dict[str, object]) -> str:
    """Helper for debugging/manual dumps."""
    return json.dumps(release, sort_keys=True)
