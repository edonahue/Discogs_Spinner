import logging
from datetime import datetime, timezone

from discogs_player.core.settings import get_discogs_token
from discogs_player.data.db import get_connection
from discogs_player.services.discogs_client import DiscogsClient

_logger = logging.getLogger(__name__)


def run_refresh_release_stats(
    *,
    limit: int = 20,
    force_refresh: bool = False,
    is_wantlist: bool = False,
) -> dict[str, object]:
    token = get_discogs_token()
    if not token:
        return {"error": "Discogs token missing"}

    client = DiscogsClient(token=token)
    conn = get_connection()

    table = "wantlist" if is_wantlist else "releases"
    stats_table = "wantlist_stats" if is_wantlist else "release_stats"

    try:
        # Select candidates that either have no stats or stats older than 7 days
        # or just no stats if not force_refresh

        # Simple strategy: Find items in base table
        # Left join with stats table
        # Where stats are missing OR (force_refresh=True AND stats are old)

        query = f"""
            SELECT r.discogs_release_id
            FROM {table} r
            LEFT JOIN {stats_table} s ON r.discogs_release_id = s.discogs_release_id
            WHERE r.is_active = 1
            AND (s.last_updated_at IS NULL OR s.last_updated_at < date('now', '-7 days') OR ?)
            ORDER BY s.last_updated_at ASC NULLS FIRST
            LIMIT ?
        """

        rows = conn.execute(query, (force_refresh, limit)).fetchall()
        release_ids = [row[0] for row in rows]

        if not release_ids:
            return {"status": "No candidates found", "processed": 0}

        success_count = 0
        error_count = 0

        # We can parallelize this slightly, but be careful with rate limits.
        # Discogs limit is 60/min.
        # Serial execution with 1s sleep on 429 is safest for now, or a small pool.
        # Let's do serial for safety first.

        for release_id in release_ids:
            try:
                stats = client.fetch_release_stats(release_id)
                now = datetime.now(timezone.utc).isoformat()

                conn.execute(
                    f"""
                    INSERT INTO {stats_table} (
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
                        release_id,
                        stats.get("num_for_sale"),
                        stats.get("lowest_price"),
                        stats.get("community_have"),
                        stats.get("community_want"),
                        stats.get("rating_count"),
                        stats.get("rating_average"),
                        now,
                    ),
                )
                conn.commit()
                success_count += 1
                # Tiny sleep to be nice?
                # time.sleep(0.5)

            except Exception as e:
                _logger.error(f"Failed to refresh stats for {release_id}: {e}")
                error_count += 1

        return {
            "status": "completed",
            "processed": len(release_ids),
            "success": success_count,
            "errors": error_count,
            "is_wantlist": is_wantlist,
        }

    finally:
        conn.close()
