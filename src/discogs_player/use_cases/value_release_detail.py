"""Load and refresh source-aware release details for the Value workspace."""

from __future__ import annotations

from datetime import datetime, timezone

from discogs_player.core.settings import (
    discogs_token_missing_message,
    get_discogs_token,
)
from discogs_player.data.db import get_connection
from discogs_player.data.repo import (
    get_release_by_id,
    get_wantlist_by_id,
    upsert_market_price,
    upsert_wantlist_market_price,
)
from discogs_player.services.discogs_client import DiscogsClient
from discogs_player.services.sync_manager import MissingDiscogsTokenError

_COLLECTION_SOURCE = "collection"
_WANTLIST_SOURCE = "wantlist"


def _normalize_source(source: str) -> str:
    normalized = str(source or "").strip().lower()
    if normalized not in {_COLLECTION_SOURCE, _WANTLIST_SOURCE}:
        raise ValueError("source must be 'collection' or 'wantlist'")
    return normalized


def _source_label(source: str) -> str:
    return "Wantlist" if source == _WANTLIST_SOURCE else "Collection"


def _discogs_release_url(release_id: int) -> str:
    return f"https://www.discogs.com/release/{int(release_id)}"


def _discogs_marketplace_url(release_id: int) -> str:
    return f"https://www.discogs.com/sell/release/{int(release_id)}"


def _as_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return int(text)
        except ValueError:
            return None
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _as_float(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _as_nonempty_str(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def build_value_release_record(
    source: str,
    item: dict[str, object],
) -> dict[str, object]:
    normalized_source = _normalize_source(source)
    result = dict(item)
    release_id = _as_int(result.get("discogs_release_id")) or 0

    result["source"] = normalized_source
    result["source_label"] = _source_label(normalized_source)
    result["discogs_release_url"] = (
        _discogs_release_url(release_id) if release_id > 0 else None
    )
    result["discogs_marketplace_url"] = (
        _discogs_marketplace_url(release_id) if release_id > 0 else None
    )

    lowest = result.get("market_lowest")
    median = result.get("market_median")
    highest = result.get("market_highest")
    has_market_value = any(
        isinstance(value, (int, float)) for value in (lowest, median, highest)
    )
    result["has_market_value"] = has_market_value

    if isinstance(lowest, (int, float)) and isinstance(highest, (int, float)):
        result["market_spread"] = float(highest) - float(lowest)
        result["market_midpoint"] = (float(highest) + float(lowest)) / 2.0
    elif isinstance(median, (int, float)):
        result["market_spread"] = None
        result["market_midpoint"] = float(median)
    else:
        result["market_spread"] = None
        result["market_midpoint"] = None

    result["market_price_point_count"] = sum(
        1 for value in (lowest, median, highest) if isinstance(value, (int, float))
    )
    result["search_display"] = " - ".join(
        part
        for part in (
            str(result.get("artist") or "").strip(),
            str(result.get("title") or "").strip(),
        )
        if part
    ) or f"Release {release_id}"
    return result


def _load_local_value_release(
    conn,
    *,
    source: str,
    release_id: int,
) -> dict[str, object]:
    normalized_source = _normalize_source(source)
    normalized_release_id = int(release_id)
    if normalized_release_id <= 0:
        raise ValueError("release_id must be a positive integer")

    if normalized_source == _WANTLIST_SOURCE:
        item = get_wantlist_by_id(
            conn,
            normalized_release_id,
            include_market=True,
        )
        if item is None:
            raise ValueError(f"Wantlist release not found: {normalized_release_id}")
        return dict(item)

    item = get_release_by_id(
        conn,
        normalized_release_id,
        include_market=True,
    )
    if item is None:
        raise ValueError(f"Collection release not found: {normalized_release_id}")
    return dict(item)


def run_get_value_release_detail(
    source: str,
    release_id: int,
) -> dict[str, object]:
    normalized_source = _normalize_source(source)
    conn = get_connection()
    try:
        item = _load_local_value_release(
            conn,
            source=normalized_source,
            release_id=release_id,
        )
    finally:
        conn.close()
    return build_value_release_record(normalized_source, item)


def _upsert_release_stats(
    conn,
    *,
    source: str,
    release_id: int,
    refreshed_at: str,
    payload: dict[str, object],
) -> None:
    table = "wantlist_stats" if source == _WANTLIST_SOURCE else "release_stats"
    conn.execute(
        f"""
        INSERT INTO {table}(
            discogs_release_id,
            num_for_sale,
            lowest_price,
            community_have,
            community_want,
            rating_count,
            rating_average,
            last_updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(discogs_release_id) DO UPDATE SET
            num_for_sale = excluded.num_for_sale,
            lowest_price = excluded.lowest_price,
            community_have = excluded.community_have,
            community_want = excluded.community_want,
            rating_count = excluded.rating_count,
            rating_average = excluded.rating_average,
            last_updated_at = excluded.last_updated_at
        """,
        (
            int(release_id),
            payload.get("num_for_sale"),
            payload.get("lowest_price"),
            payload.get("community_have"),
            payload.get("community_want"),
            payload.get("rating_count"),
            payload.get("rating_average"),
            refreshed_at,
        ),
    )


def run_refresh_value_release_detail(
    source: str,
    release_id: int,
) -> dict[str, object]:
    normalized_source = _normalize_source(source)
    normalized_release_id = int(release_id)
    if normalized_release_id <= 0:
        raise ValueError("release_id must be a positive integer")

    token = get_discogs_token()
    if not token:
        raise MissingDiscogsTokenError(discogs_token_missing_message())

    client = DiscogsClient(token=token)
    refreshed_at = datetime.now(timezone.utc).isoformat()
    price_payload = client.fetch_market_price_suggestions(normalized_release_id)
    stats_payload = client.fetch_release_stats(normalized_release_id)
    price_lowest = _as_float(price_payload.get("lowest"))
    price_median = _as_float(price_payload.get("median"))
    price_highest = _as_float(price_payload.get("highest"))
    price_currency = _as_nonempty_str(price_payload.get("currency"))

    conn = get_connection()
    try:
        _load_local_value_release(
            conn,
            source=normalized_source,
            release_id=normalized_release_id,
        )
        if normalized_source == _WANTLIST_SOURCE:
            upsert_wantlist_market_price(
                conn,
                discogs_release_id=normalized_release_id,
                lowest=price_lowest,
                median=price_median,
                highest=price_highest,
                currency=price_currency,
                last_updated_at=refreshed_at,
                commit=False,
            )
        else:
            upsert_market_price(
                conn,
                discogs_release_id=normalized_release_id,
                lowest=price_lowest,
                median=price_median,
                highest=price_highest,
                currency=price_currency,
                last_updated_at=refreshed_at,
                commit=False,
            )
        _upsert_release_stats(
            conn,
            source=normalized_source,
            release_id=normalized_release_id,
            refreshed_at=refreshed_at,
            payload=stats_payload,
        )
        conn.commit()
    finally:
        conn.close()

    result = run_get_value_release_detail(normalized_source, normalized_release_id)
    result["refreshed_at"] = refreshed_at
    return result
