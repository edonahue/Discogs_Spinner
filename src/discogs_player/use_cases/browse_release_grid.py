"""Use-case for GUI release browsing with optional cover prefetch."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from discogs_player.services.high_res_art import (
    get_high_res_art_preference,
    resolve_cover_url_for_preference,
)
from discogs_player.services.image_cache import get_or_fetch_cover_path
from discogs_player.performance import cover_worker_count
from discogs_player.use_cases.list_releases import run_list_releases

_BROWSE_COVER_PRELOAD_MAX_WORKERS = cover_worker_count


def run_browse_release_grid(
    *,
    limit: int | None = None,
    q: str | None = None,
    year: str | None = None,
    genres: list[str] | None = None,
    styles: list[str] | None = None,
    unmatched: bool = False,
    preload_covers: bool = True,
) -> list[dict[str, object]]:
    prefer_high_res, high_res_target_size = get_high_res_art_preference()
    releases = run_list_releases(
        limit=limit,
        q=q,
        year=year,
        genres=genres or [],
        styles=styles or [],
        unmatched=unmatched,
        with_value=True,
    )

    items: list[dict[str, object]] = []
    cover_url_to_indices: dict[str, list[int]] = {}
    for release in releases:
        raw_cover_url = str(release.get("cover_url") or "").strip() or None
        cover_url = resolve_cover_url_for_preference(
            raw_cover_url,
            prefer_high_res=prefer_high_res,
            target_size=high_res_target_size,
        )

        items.append(
            {
                "discogs_release_id": release.get("discogs_release_id"),
                "artist": release.get("artist"),
                "title": release.get("title"),
                "year": release.get("year"),
                "genres": release.get("genres")
                if isinstance(release.get("genres"), list)
                else [],
                "styles": release.get("styles")
                if isinstance(release.get("styles"), list)
                else [],
                "thumb_url": release.get("thumb_url"),
                "cover_url": cover_url,
                "cover_path": None,
                "added_at": release.get("added_at"),
                "last_synced_at": release.get("last_synced_at"),
                "is_active": release.get("is_active"),
                "spotify_album_id": release.get("spotify_album_id"),
                "market_lowest": release.get("market_lowest"),
                "market_median": release.get("market_median"),
                "market_highest": release.get("market_highest"),
                "market_currency": release.get("market_currency"),
                "market_last_updated_at": release.get("market_last_updated_at"),
                "num_for_sale": release.get("num_for_sale"),
                "lowest_price": release.get("lowest_price"),
                "community_have": release.get("community_have"),
                "community_want": release.get("community_want"),
                "rating_count": release.get("rating_count"),
                "rating_average": release.get("rating_average"),
            }
        )
        if preload_covers and cover_url:
            cover_url_to_indices.setdefault(cover_url, []).append(len(items) - 1)

    if preload_covers and cover_url_to_indices:
        max_workers = min(
            _BROWSE_COVER_PRELOAD_MAX_WORKERS(),
            len(cover_url_to_indices),
        )
        with ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="browse-cover"
        ) as executor:
            future_to_cover_url = {
                executor.submit(get_or_fetch_cover_path, cover_url): cover_url
                for cover_url in cover_url_to_indices
            }
            for future in as_completed(future_to_cover_url):
                cover_url = future_to_cover_url[future]
                try:
                    cover_path = future.result()
                except Exception:
                    cover_path = None
                if not cover_path:
                    continue
                for item_index in cover_url_to_indices.get(cover_url, []):
                    items[item_index]["cover_path"] = cover_path

    return items
