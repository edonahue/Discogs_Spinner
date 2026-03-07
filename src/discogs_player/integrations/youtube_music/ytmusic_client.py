"""YouTube Music search client (unauthenticated, v1)."""

from __future__ import annotations

from discogs_player.integrations.player_backend import PlayerApiError


def _safe_str(value: object) -> str:
    if isinstance(value, str):
        return value
    return ""


def _safe_int(value: object, *, default: int = 0) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return default


def _extract_year(result: dict[str, object]) -> int | None:
    raw = result.get("year")
    if isinstance(raw, int) and not isinstance(raw, bool):
        return raw
    if isinstance(raw, str) and raw.isdigit():
        return int(raw)
    return None


def _normalise_result(result: dict[str, object]) -> dict[str, object]:
    """Convert a ytmusicapi album search result to the MatchingService schema."""
    browse_id = _safe_str(result.get("browseId"))
    title = _safe_str(result.get("title"))

    raw_artists = result.get("artists") or []
    artists: list[dict[str, object]] = []
    if isinstance(raw_artists, list):
        for a in raw_artists:
            if isinstance(a, dict):
                name = _safe_str(a.get("name"))
                if name:
                    artists.append({"name": name})

    release_date = _extract_year(result)
    track_count = _safe_int(result.get("trackCount"))

    return {
        "id": browse_id,
        "name": title,
        "artists": artists,
        "release_date": release_date,
        "total_tracks": track_count,
    }


class YouTubeMusicClient:
    """Thin wrapper around ytmusicapi for unauthenticated album search."""

    def search_albums(self, query: str, limit: int = 10) -> list[dict[str, object]]:
        """Search YouTube Music for albums matching *query*.

        Returns a list normalised to the schema MatchingService expects:
        ``{"id": browseId, "name": title, "artists": [...], "release_date": year,
        "total_tracks": count}``
        """
        try:
            import ytmusicapi  # type: ignore[import-untyped]
        except ImportError as exc:
            raise PlayerApiError(
                "ytmusicapi is not installed. Add it with `pip install ytmusicapi`."
            ) from exc

        try:
            yt = ytmusicapi.YTMusic()
            raw = yt.search(query, filter="albums", limit=limit)
        except Exception as exc:
            raise PlayerApiError(f"YouTube Music search failed: {exc}") from exc

        if not isinstance(raw, list):
            return []

        results: list[dict[str, object]] = []
        for item in raw:
            if isinstance(item, dict):
                results.append(_normalise_result(item))
        return results
