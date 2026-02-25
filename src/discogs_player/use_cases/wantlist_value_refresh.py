"""Refresh cached market value stats for a wantlist release."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from discogs_player.core.settings import (
    discogs_token_missing_message,
    get_discogs_token,
)
from discogs_player.data.db import get_connection
from discogs_player.data.repo import (
    get_wantlist_by_id,
    upsert_wantlist_market_price,
)
from discogs_player.services.discogs_client import DiscogsApiError, DiscogsClient
from discogs_player.services.sync_manager import MissingDiscogsTokenError


def _normalize_release_ids(release_ids: list[int] | None) -> list[int]:
    if not release_ids:
        return []

    normalized: list[int] = []
    seen: set[int] = set()
    for raw in release_ids:
        release_id = int(raw)
        if release_id <= 0:
            raise ValueError("release_ids must contain positive integers")
        if release_id in seen:
            continue
        seen.add(release_id)
        normalized.append(release_id)
    return normalized


def _as_float_or_none(value: object | None) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _as_nonempty_str_or_none(value: object | None) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def run_refresh_wantlist_market_value(release_id: int) -> dict[str, object]:
    normalized_release_id = int(release_id)
    if normalized_release_id <= 0:
        raise ValueError("release_id must be a positive integer")

    token = get_discogs_token()
    if not token:
        raise MissingDiscogsTokenError(discogs_token_missing_message())

    now_iso = datetime.now(timezone.utc).isoformat()
    client = DiscogsClient(token=token)
    stats = client.fetch_market_price_suggestions(normalized_release_id)

    lowest = stats.get("lowest")
    median = stats.get("median")
    highest = stats.get("highest")
    currency = stats.get("currency")

    conn = get_connection()
    try:
        entry = get_wantlist_by_id(conn, normalized_release_id, include_market=True)
        if entry is None:
            raise ValueError(f"Wantlist release not found: {normalized_release_id}")
        upsert_wantlist_market_price(
            conn,
            discogs_release_id=normalized_release_id,
            lowest=float(lowest) if isinstance(lowest, (int, float)) else None,
            median=float(median) if isinstance(median, (int, float)) else None,
            highest=float(highest) if isinstance(highest, (int, float)) else None,
            currency=str(currency).strip()
            if isinstance(currency, str) and currency.strip()
            else None,
            last_updated_at=now_iso,
        )
        updated = (
            get_wantlist_by_id(conn, normalized_release_id, include_market=True)
            or entry
        )
    finally:
        conn.close()

    updated = dict(updated)
    updated["refreshed_at"] = now_iso
    return updated


def run_refresh_wantlist_market_values(
    *,
    limit: int = 100,
    stale_days: int = 30,
    release_ids: list[int] | None = None,
) -> dict[str, object]:
    if limit < 1:
        raise ValueError("limit must be >= 1")
    if stale_days < 0:
        raise ValueError("stale_days must be >= 0")

    normalized_release_ids = _normalize_release_ids(release_ids)

    token = get_discogs_token()
    if not token:
        raise MissingDiscogsTokenError(discogs_token_missing_message())

    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    stale_before = (now - timedelta(days=int(stale_days))).isoformat()

    skipped_release_ids: list[int] = []
    conn = get_connection()
    try:
        if normalized_release_ids:
            placeholders = ", ".join(["?"] * len(normalized_release_ids))
            rows = conn.execute(
                (
                    "SELECT discogs_release_id FROM wantlist "
                    "WHERE is_active = 1 AND discogs_release_id IN ("
                    + placeholders
                    + ")"
                ),
                normalized_release_ids,
            ).fetchall()
            available = {int(row["discogs_release_id"]) for row in rows}
            candidate_ids = [
                release_id
                for release_id in normalized_release_ids
                if release_id in available
            ]
            skipped_release_ids = [
                release_id
                for release_id in normalized_release_ids
                if release_id not in available
            ]
        else:
            rows = conn.execute(
                """
                SELECT w.discogs_release_id
                FROM wantlist w
                LEFT JOIN wantlist_market_prices wmp
                  ON wmp.discogs_release_id = w.discogs_release_id
                WHERE w.is_active = 1
                  AND (wmp.last_updated_at IS NULL OR wmp.last_updated_at < ?)
                ORDER BY COALESCE(wmp.last_updated_at, ''), w.discogs_release_id
                LIMIT ?
                """,
                (stale_before, int(limit)),
            ).fetchall()
            candidate_ids = [int(row["discogs_release_id"]) for row in rows]
    finally:
        conn.close()

    client = DiscogsClient(token=token)
    refreshed_count = 0
    priced_count = 0
    unpriced_count = 0
    error_count = 0
    updated_release_ids: list[int] = []
    failed_release_ids: list[int] = []
    warnings: list[str] = []

    conn = get_connection()
    try:
        for release_id in candidate_ids:
            try:
                stats = client.fetch_market_price_suggestions(release_id)
            except DiscogsApiError as exc:
                error_count += 1
                failed_release_ids.append(int(release_id))
                warnings.append(f"release_id={release_id}: {exc}")
                continue

            lowest = _as_float_or_none(stats.get("lowest"))
            median = _as_float_or_none(stats.get("median"))
            highest = _as_float_or_none(stats.get("highest"))
            currency = _as_nonempty_str_or_none(stats.get("currency"))

            upsert_wantlist_market_price(
                conn,
                discogs_release_id=int(release_id),
                lowest=lowest,
                median=median,
                highest=highest,
                currency=currency,
                last_updated_at=now_iso,
                commit=False,
            )
            refreshed_count += 1
            updated_release_ids.append(int(release_id))
            if any(value is not None for value in (lowest, median, highest)):
                priced_count += 1
            else:
                unpriced_count += 1
        if refreshed_count > 0:
            conn.commit()
    finally:
        conn.close()

    return {
        "ok": True,
        "limit": int(limit),
        "stale_days": int(stale_days),
        "stale_before": stale_before,
        "release_ids_requested": normalized_release_ids,
        "candidate_count": len(candidate_ids),
        "refreshed_count": refreshed_count,
        "priced_count": priced_count,
        "unpriced_count": unpriced_count,
        "error_count": error_count,
        "updated_release_ids": updated_release_ids,
        "failed_release_ids": failed_release_ids,
        "skipped_release_ids": skipped_release_ids,
        "warnings": warnings,
        "last_refresh_time": now_iso,
    }
