"""Use-case for GUI wantlist browsing with optional cover prefetch."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from discogs_player.services.high_res_art import (
    get_high_res_art_preference,
    resolve_cover_url_for_preference,
)
from discogs_player.services.image_cache import get_or_fetch_cover_path
from discogs_player.performance import cover_worker_count
from discogs_player.use_cases.list_wantlist import run_list_wantlist

_BROWSE_COVER_PRELOAD_MAX_WORKERS = cover_worker_count


def run_browse_wantlist_grid(
    *,
    limit: int | None = None,
    q: str | None = None,
    year: str | None = None,
    genres: list[str] | None = None,
    styles: list[str] | None = None,
    preload_covers: bool = True,
) -> list[dict[str, object]]:
    prefer_high_res, high_res_target_size = get_high_res_art_preference()
    entries = run_list_wantlist(
        limit=limit or 25,
        q=q,
        year=year,
        genres=genres or [],
        styles=styles or [],
        with_value=True,
    )

    items: list[dict[str, object]] = []
    cover_url_to_indices: dict[str, list[int]] = {}
    for entry in entries:
        raw_cover_url = str(entry.get("cover_url") or "").strip() or None
        cover_url = resolve_cover_url_for_preference(
            raw_cover_url,
            prefer_high_res=prefer_high_res,
            target_size=high_res_target_size,
        )
        items.append(
            {
                "discogs_release_id": entry.get("discogs_release_id"),
                "artist": entry.get("artist"),
                "title": entry.get("title"),
                "year": entry.get("year"),
                "genres": entry.get("genres")
                if isinstance(entry.get("genres"), list)
                else [],
                "styles": entry.get("styles")
                if isinstance(entry.get("styles"), list)
                else [],
                "thumb_url": entry.get("thumb_url"),
                "cover_url": cover_url,
                "cover_path": None,
                "notes": entry.get("notes"),
                "added_at": entry.get("added_at"),
                "last_synced_at": entry.get("last_synced_at"),
                "is_active": entry.get("is_active"),
                "spotify_album_id": entry.get("spotify_album_id"),
                "market_lowest": entry.get("market_lowest"),
                "market_median": entry.get("market_median"),
                "market_highest": entry.get("market_highest"),
                "market_currency": entry.get("market_currency"),
                "market_last_updated_at": entry.get("market_last_updated_at"),
                "num_for_sale": entry.get("num_for_sale"),
                "lowest_price": entry.get("lowest_price"),
                "community_have": entry.get("community_have"),
                "community_want": entry.get("community_want"),
                "rating_count": entry.get("rating_count"),
                "rating_average": entry.get("rating_average"),
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
            max_workers=max_workers, thread_name_prefix="wantlist-cover"
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
