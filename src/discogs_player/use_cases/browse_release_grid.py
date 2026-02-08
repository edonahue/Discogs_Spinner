"""Use-case for GUI release browsing with optional cover prefetch."""

from __future__ import annotations

from discogs_player.services.image_cache import get_or_fetch_cover_path
from discogs_player.use_cases.list_releases import run_list_releases


def run_browse_release_grid(
    *,
    limit: int = 50,
    q: str | None = None,
    year: str | None = None,
    genres: list[str] | None = None,
    styles: list[str] | None = None,
    unmatched: bool = False,
    preload_covers: bool = True,
) -> list[dict[str, object]]:
    releases = run_list_releases(
        limit=limit,
        q=q,
        year=year,
        genres=genres or [],
        styles=styles or [],
        unmatched=unmatched,
    )

    items: list[dict[str, object]] = []
    for release in releases:
        cover_url = str(release.get("cover_url") or "").strip() or None
        cover_path = get_or_fetch_cover_path(cover_url) if preload_covers else None

        items.append(
            {
                "discogs_release_id": release.get("discogs_release_id"),
                "artist": release.get("artist"),
                "title": release.get("title"),
                "year": release.get("year"),
                "genres": release.get("genres") if isinstance(release.get("genres"), list) else [],
                "styles": release.get("styles") if isinstance(release.get("styles"), list) else [],
                "cover_url": cover_url,
                "cover_path": cover_path,
                "spotify_album_id": release.get("spotify_album_id"),
            }
        )

    return items
