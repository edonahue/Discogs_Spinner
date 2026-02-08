"""Show cached market value stats for one release."""

from __future__ import annotations

from datetime import datetime, timezone

from discogs_player.core.settings import get_discogs_token
from discogs_player.data.db import get_connection
from discogs_player.data.repo import get_market_price, get_release_by_id, upsert_market_price
from discogs_player.services.discogs_client import DiscogsClient
from discogs_player.services.sync_manager import MissingDiscogsTokenError


def run_market_value_show(release_id: int, *, refresh: bool = False) -> dict[str, object]:
    normalized_release_id = int(release_id)
    if normalized_release_id <= 0:
        raise ValueError("release_id must be a positive integer")

    conn = get_connection()
    try:
        release = get_release_by_id(conn, normalized_release_id)
        if release is None:
            raise ValueError(f"Release not found: {normalized_release_id}")
        price = get_market_price(conn, normalized_release_id)
    finally:
        conn.close()

    if refresh:
        token = get_discogs_token()
        if not token:
            raise MissingDiscogsTokenError(
                "DISCOGS_TOKEN is not set. Export it in your shell or store it in app_settings."
            )
        stats = DiscogsClient(token=token).fetch_market_price_suggestions(normalized_release_id)
        now_iso = datetime.now(timezone.utc).isoformat()

        conn = get_connection()
        try:
            upsert_market_price(
                conn,
                discogs_release_id=normalized_release_id,
                lowest=float(stats["lowest"]) if isinstance(stats.get("lowest"), (int, float)) else None,
                median=float(stats["median"]) if isinstance(stats.get("median"), (int, float)) else None,
                highest=float(stats["highest"]) if isinstance(stats.get("highest"), (int, float)) else None,
                currency=(
                    str(stats["currency"]).strip()
                    if isinstance(stats.get("currency"), str) and str(stats["currency"]).strip()
                    else None
                ),
                last_updated_at=now_iso,
            )
            price = get_market_price(conn, normalized_release_id)
        finally:
            conn.close()

    result = dict(release)
    result["market_lowest"] = price["lowest"] if price else None
    result["market_median"] = price["median"] if price else None
    result["market_highest"] = price["highest"] if price else None
    result["market_currency"] = price["currency"] if price else None
    result["market_last_updated_at"] = price["last_updated_at"] if price else None
    result["has_market_value"] = bool(
        price
        and any(
            isinstance(price.get(key), (int, float))
            for key in ("lowest", "median", "highest")
        )
    )
    lowest = price["lowest"] if price else None
    highest = price["highest"] if price else None
    if isinstance(lowest, (int, float)) and isinstance(highest, (int, float)):
        result["market_spread"] = float(highest) - float(lowest)
        result["market_midpoint"] = (float(highest) + float(lowest)) / 2.0
    else:
        result["market_spread"] = None
        result["market_midpoint"] = None
    result["market_price_point_count"] = (
        sum(
            1
            for key in ("lowest", "median", "highest")
            if price and isinstance(price.get(key), (int, float))
        )
        if price
        else 0
    )
    return result
