"""Refresh cached market value stats for active collection releases."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from discogs_player.core.settings import get_discogs_token
from discogs_player.data.db import get_connection
from discogs_player.data.repo import (
    query_market_price_refresh_candidates,
    query_releases_needing_market_refresh,
    upsert_market_price,
)
from discogs_player.services.discogs_client import DiscogsApiError, DiscogsClient
from discogs_player.services.sync_manager import MissingDiscogsTokenError


def run_refresh_market_values(
    *,
    limit: int = 100,
    stale_days: int = 30,
    release_ids: list[int] | None = None,
    from_missing: bool = False,
) -> dict[str, object]:
    if limit < 1:
        raise ValueError("limit must be >= 1")
    if stale_days < 0:
        raise ValueError("stale_days must be >= 0")
    normalized_release_ids: list[int] = []
    if release_ids:
        seen: set[int] = set()
        for raw in release_ids:
            release_id = int(raw)
            if release_id <= 0:
                raise ValueError("release_ids must contain positive integers")
            if release_id in seen:
                continue
            seen.add(release_id)
            normalized_release_ids.append(release_id)
    if from_missing and normalized_release_ids:
        raise ValueError("Cannot combine from_missing=True with explicit release_ids.")

    token = get_discogs_token()
    if not token:
        raise MissingDiscogsTokenError(
            "DISCOGS_TOKEN is not set. Export it in your shell or store it in app_settings."
        )

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
                    "SELECT discogs_release_id FROM releases "
                    "WHERE is_active = 1 AND discogs_release_id IN (" + placeholders + ")"
                ),
                normalized_release_ids,
            ).fetchall()
            available = {int(row["discogs_release_id"]) for row in rows}
            candidate_ids = [release_id for release_id in normalized_release_ids if release_id in available]
            skipped_release_ids = [
                release_id for release_id in normalized_release_ids if release_id not in available
            ]
        elif from_missing:
            missing_rows = query_releases_needing_market_refresh(
                conn,
                limit=limit,
                stale_before=stale_before,
                include_market=False,
            )
            candidate_ids = [int(item["discogs_release_id"]) for item in missing_rows]
        else:
            candidate_ids = query_market_price_refresh_candidates(
                conn,
                stale_before=stale_before,
                limit=limit,
            )
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

            lowest = stats.get("lowest")
            median = stats.get("median")
            highest = stats.get("highest")
            currency = stats.get("currency")

            upsert_market_price(
                conn,
                discogs_release_id=int(release_id),
                lowest=float(lowest) if isinstance(lowest, (int, float)) else None,
                median=float(median) if isinstance(median, (int, float)) else None,
                highest=float(highest) if isinstance(highest, (int, float)) else None,
                currency=str(currency).strip() if isinstance(currency, str) and currency.strip() else None,
                last_updated_at=now_iso,
            )
            refreshed_count += 1
            updated_release_ids.append(int(release_id))
            if any(isinstance(value, (int, float)) for value in (lowest, median, highest)):
                priced_count += 1
            else:
                unpriced_count += 1
    finally:
        conn.close()

    return {
        "ok": True,
        "limit": int(limit),
        "stale_days": int(stale_days),
        "stale_before": stale_before,
        "release_ids_requested": normalized_release_ids,
        "from_missing": bool(from_missing),
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
