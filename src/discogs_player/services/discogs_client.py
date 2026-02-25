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


def _coerce_positive_int(value: object | None, *, default: int = 1) -> int:
    if isinstance(value, bool):
        parsed = int(value)
    elif isinstance(value, int):
        parsed = value
    elif isinstance(value, float):
        parsed = int(value)
    elif isinstance(value, str):
        stripped = value.strip()
        if not stripped or not stripped.lstrip("-").isdigit():
            return default
        parsed = int(stripped)
    else:
        return default
    return parsed if parsed > 0 else default


def _as_dict_list(value: object | None) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, object]] = []
    for item in value:
        if isinstance(item, dict):
            rows.append(item)
    return rows


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
            except (
                Exception
            ) as exc:  # pragma: no cover - explicit branch tested via fake client
                if isinstance(exc, httpx_module.RequestError):
                    if attempt < max_attempts:
                        time.sleep(attempt)
                        continue
                    raise DiscogsApiError(
                        f"Discogs request transport error: {exc}"
                    ) from exc
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

        raise DiscogsApiError(
            "Discogs API retries exhausted due to rate limiting/server errors"
        )

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
            raise DiscogsApiError(
                "Discogs identity response was not valid JSON"
            ) from exc

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

        with httpx_module.Client(
            headers=self._headers(), timeout=self.timeout_seconds
        ) as client:
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
                    raise DiscogsApiError(
                        "Discogs collection response was not valid JSON"
                    ) from exc

                pagination_raw = payload.get("pagination")
                pagination = pagination_raw if isinstance(pagination_raw, dict) else {}
                pages = _coerce_positive_int(pagination.get("pages"), default=1)
                page_releases = _as_dict_list(payload.get("releases"))

                now = datetime.now(timezone.utc).isoformat()
                normalized: list[dict[str, object]] = []
                for item in page_releases:
                    normalized_item = self._normalize_release(item, now)
                    if normalized_item is not None:
                        normalized.append(normalized_item)
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

        with httpx_module.Client(
            headers=self._headers(), timeout=self.timeout_seconds
        ) as client:
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
                    raise DiscogsApiError(
                        "Discogs wantlist response was not valid JSON"
                    ) from exc

                pagination_raw = payload.get("pagination")
                pagination = pagination_raw if isinstance(pagination_raw, dict) else {}
                pages = _coerce_positive_int(pagination.get("pages"), default=1)
                page_releases = _as_dict_list(payload.get("wants"))

                now = datetime.now(timezone.utc).isoformat()
                normalized: list[dict[str, object]] = []
                for item in page_releases:
                    normalized_item = self._normalize_wantlist_release(item, now)
                    if normalized_item is not None:
                        normalized.append(normalized_item)
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

    def fetch_market_price_suggestions(
        self, discogs_release_id: int
    ) -> dict[str, object]:
        httpx_module = _httpx()
        with httpx_module.Client(
            headers=self._headers(), timeout=self.timeout_seconds
        ) as client:
            response = self._request_with_backoff(
                client,
                "GET",
                f"/marketplace/price_suggestions/{int(discogs_release_id)}",
                httpx_module=httpx_module,
            )
            try:
                payload = response.json()
            except ValueError as exc:
                raise DiscogsApiError(
                    "Discogs market value response was not valid JSON"
                ) from exc
        return self._extract_market_price_suggestions(payload)

    def fetch_release_tracklist(self, discogs_release_id: int) -> dict[str, object]:
        normalized_release_id = int(discogs_release_id)
        if normalized_release_id <= 0:
            raise ValueError("discogs_release_id must be a positive integer")

        httpx_module = _httpx()
        with httpx_module.Client(
            headers=self._headers(), timeout=self.timeout_seconds
        ) as client:
            response = self._request_with_backoff(
                client,
                "GET",
                f"/releases/{normalized_release_id}",
                httpx_module=httpx_module,
            )
            try:
                payload = response.json()
            except ValueError as exc:
                raise DiscogsApiError(
                    "Discogs release detail response was not valid JSON"
                ) from exc

        return {
            "discogs_release_id": normalized_release_id,
            "tracks": self._extract_release_tracklist(payload),
        }

    def fetch_release_stats(self, discogs_release_id: int) -> dict[str, object]:
        normalized_release_id = int(discogs_release_id)
        if normalized_release_id <= 0:
            raise ValueError("discogs_release_id must be a positive integer")

        httpx_module = _httpx()
        with httpx_module.Client(
            headers=self._headers(), timeout=self.timeout_seconds
        ) as client:
            response = self._request_with_backoff(
                client,
                "GET",
                f"/releases/{normalized_release_id}",
                httpx_module=httpx_module,
            )
            try:
                payload = response.json()
            except ValueError as exc:
                raise DiscogsApiError(
                    "Discogs release detail response was not valid JSON"
                ) from exc

        return self._extract_release_stats(payload)

    def _extract_release_stats(self, payload: Any) -> dict[str, object]:
        if not isinstance(payload, dict):
            raise DiscogsApiError(
                "Discogs release detail response had unexpected format"
            )

        community = payload.get("community")
        community = community if isinstance(community, dict) else {}
        rating = community.get("rating")
        rating = rating if isinstance(rating, dict) else {}

        return {
            "num_for_sale": payload.get("num_for_sale"),
            "lowest_price": payload.get("lowest_price"),
            "community_have": community.get("have"),
            "community_want": community.get("want"),
            "rating_count": rating.get("count"),
            "rating_average": rating.get("average"),
        }

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

    def _extract_release_tracklist(self, payload: Any) -> list[dict[str, object]]:
        if not isinstance(payload, dict):
            raise DiscogsApiError(
                "Discogs release detail response had unexpected format"
            )

        rows = payload.get("tracklist")
        if rows is None:
            return []
        if not isinstance(rows, list):
            raise DiscogsApiError(
                "Discogs release detail tracklist had unexpected format"
            )

        tracks: list[dict[str, object]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            title = str(row.get("title") or "").strip()
            position = str(row.get("position") or "").strip()
            duration = str(row.get("duration") or "").strip()
            type_value = str(row.get("type_") or "").strip()
            normalized_type = type_value.lower()
            tracks.append(
                {
                    "position": position or None,
                    "title": title or None,
                    "duration": duration or None,
                    "type": type_value or None,
                    "is_audio_track": normalized_type == "track" and bool(title),
                }
            )
        return tracks

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

        artists_raw = basic.get("artists")
        artists = artists_raw if isinstance(artists_raw, list) else []
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

        genres_raw = basic.get("genres")
        styles_raw = basic.get("styles")
        genres = genres_raw if isinstance(genres_raw, list) else []
        styles = styles_raw if isinstance(styles_raw, list) else []

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
