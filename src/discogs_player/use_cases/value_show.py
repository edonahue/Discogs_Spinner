"""Show cached market value stats for one release."""

from __future__ import annotations

from datetime import datetime, timezone

from discogs_player.core.settings import (
    discogs_token_missing_message,
    get_discogs_token,
)
from discogs_player.data.db import get_connection
from discogs_player.data.repo import (
    get_market_price,
    get_release_by_id,
    upsert_market_price,
)
from discogs_player.services.discogs_client import DiscogsClient
from discogs_player.services.sync_manager import MissingDiscogsTokenError


def _as_float_or_none(value: object | None) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def run_market_value_show(
    release_id: int, *, refresh: bool = False
) -> dict[str, object]:
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
            raise MissingDiscogsTokenError(discogs_token_missing_message())
        stats = DiscogsClient(token=token).fetch_market_price_suggestions(
            normalized_release_id
        )
        now_iso = datetime.now(timezone.utc).isoformat()

        conn = get_connection()
        try:
            lowest = _as_float_or_none(stats.get("lowest"))
            median = _as_float_or_none(stats.get("median"))
            highest = _as_float_or_none(stats.get("highest"))
            currency_raw = stats.get("currency")
            currency = (
                str(currency_raw).strip()
                if isinstance(currency_raw, str) and currency_raw.strip()
                else None
            )
            upsert_market_price(
                conn,
                discogs_release_id=normalized_release_id,
                lowest=lowest,
                median=median,
                highest=highest,
                currency=currency,
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
