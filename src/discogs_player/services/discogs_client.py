"""Discogs API client for collection sync."""

from __future__ import annotations

import json
import statistics
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable


class DiscogsError(Exception):
    """Base class for Discogs client errors."""


class DiscogsAuthError(DiscogsError):
    """Discogs authentication failure."""


class DiscogsApiError(DiscogsError):
    """Discogs API failure."""


class DiscogsDependencyError(DiscogsError):
    """Discogs client dependency error."""


ProgressCallback = Callable[[int, int, int, int], None]


def _httpx():
    try:
        import httpx
    except ModuleNotFoundError as exc:
        raise DiscogsDependencyError(
            "Missing Python dependency: httpx. Install with `pip install -r requirements.txt`."
        ) from exc
    return httpx


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
        client: Any,
        method: str,
        path: str,
        *,
        params: dict[str, object] | None = None,
        httpx_module: Any | None = None,
    ) -> Any:
        httpx_module = httpx_module or _httpx()
        url = f"https://api.discogs.com{path}"
        max_attempts = 5

        for attempt in range(1, max_attempts + 1):
            try:
                response = client.request(method, url, params=params)
            except Exception as exc:  # pragma: no cover - explicit branch tested via fake client
                if isinstance(exc, httpx_module.RequestError):
                    if attempt < max_attempts:
                        time.sleep(attempt)
                        continue
                    raise DiscogsApiError(f"Discogs request transport error: {exc}") from exc
                raise

            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                sleep_for = (
                    int(retry_after.strip())
                    if isinstance(retry_after, str) and retry_after.strip().isdigit()
                    else attempt
                )
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

    def _get_username(self, client: Any, *, httpx_module: Any | None = None) -> str:
        response = self._request_with_backoff(
            client,
            "GET",
            "/oauth/identity",
            httpx_module=httpx_module,
        )
        try:
            payload = response.json()
        except ValueError as exc:
            raise DiscogsApiError("Discogs identity response was not valid JSON") from exc

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
        httpx_module = _httpx()

        with httpx_module.Client(headers=self._headers(), timeout=self.timeout_seconds) as client:
            username = self._get_username(client, httpx_module=httpx_module)
            page = 1
            pages = 1

            while page <= pages:
                response = self._request_with_backoff(
                    client,
                    "GET",
                    f"/users/{username}/collection/folders/0/releases",
                    params={"page": page, "per_page": per_page},
                    httpx_module=httpx_module,
                )
                try:
                    payload = response.json()
                except ValueError as exc:
                    raise DiscogsApiError("Discogs collection response was not valid JSON") from exc

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

    def fetch_wantlist_releases(
        self,
        *,
        per_page: int = 100,
        progress_callback: ProgressCallback | None = None,
    ) -> list[dict[str, object]]:
        releases: list[dict[str, object]] = []
        httpx_module = _httpx()

        with httpx_module.Client(headers=self._headers(), timeout=self.timeout_seconds) as client:
            username = self._get_username(client, httpx_module=httpx_module)
            page = 1
            pages = 1

            while page <= pages:
                response = self._request_with_backoff(
                    client,
                    "GET",
                    f"/users/{username}/wants",
                    params={"page": page, "per_page": per_page},
                    httpx_module=httpx_module,
                )
                try:
                    payload = response.json()
                except ValueError as exc:
                    raise DiscogsApiError("Discogs wantlist response was not valid JSON") from exc

                pagination = payload.get("pagination", {})
                pages = int(pagination.get("pages", 1))
                page_releases = payload.get("wants", [])

                now = datetime.now(timezone.utc).isoformat()
                normalized = [self._normalize_wantlist_release(item, now) for item in page_releases]
                normalized = [item for item in normalized if item is not None]
                releases.extend(normalized)

                if progress_callback is not None:
                    progress_callback(page, pages, len(normalized), len(releases))

                page += 1

        return releases

    def _normalize_wantlist_release(
        self,
        item: dict[str, object],
        synced_at: str,
    ) -> dict[str, object] | None:
        base = self._normalize_release(item, synced_at)
        if base is None:
            return None

        notes_raw = item.get("notes") if isinstance(item, dict) else None
        notes = str(notes_raw).strip() if notes_raw is not None else ""
        base["notes"] = notes or None
        base["is_active"] = 1
        return base

    def fetch_market_price_suggestions(self, discogs_release_id: int) -> dict[str, object]:
        httpx_module = _httpx()
        with httpx_module.Client(headers=self._headers(), timeout=self.timeout_seconds) as client:
            response = self._request_with_backoff(
                client,
                "GET",
                f"/marketplace/price_suggestions/{int(discogs_release_id)}",
                httpx_module=httpx_module,
            )
            try:
                payload = response.json()
            except ValueError as exc:
                raise DiscogsApiError("Discogs market value response was not valid JSON") from exc
        return self._extract_market_price_suggestions(payload)

    def _extract_market_price_suggestions(self, payload: Any) -> dict[str, object]:
        if not isinstance(payload, dict):
            raise DiscogsApiError("Discogs market value response had unexpected format")

        values: list[float] = []
        currency: str | None = None

        for raw in payload.values():
            if not isinstance(raw, dict):
                continue
            amount = raw.get("value")
            if isinstance(amount, (int, float)):
                values.append(float(amount))

            raw_currency = raw.get("currency")
            if currency is None and isinstance(raw_currency, str):
                raw_currency = raw_currency.strip()
                if raw_currency:
                    currency = raw_currency

        if not values:
            return {
                "lowest": None,
                "median": None,
                "highest": None,
                "currency": currency,
            }

        return {
            "lowest": float(min(values)),
            "median": float(statistics.median(values)),
            "highest": float(max(values)),
            "currency": currency,
        }

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
        year_value = None
        if isinstance(year, int):
            year_value = year
        elif isinstance(year, str):
            year_str = year.strip()
            if year_str.isdigit():
                year_value = int(year_str)

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
