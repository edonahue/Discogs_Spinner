"""Collector-focused daily-use insights aggregated from local data."""

from __future__ import annotations

from discogs_player.use_cases.collection_health import run_collection_health
from discogs_player.use_cases.hidden_gems import run_hidden_gems
from discogs_player.use_cases.setup_report import run_setup_report
from discogs_player.use_cases.status_report import get_status_report
from discogs_player.use_cases.value_refresh_queue import run_value_refresh_queue


def _as_dict(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return value
    return {}


def _as_list(value: object) -> list[object]:
    if isinstance(value, list):
        return value
    return []


def run_collector_insights(
    *,
    gems_limit: int = 5,
    queue_limit: int = 10,
    min_median: float = 25.0,
) -> dict[str, object]:
    """Build a compact collector-facing insights payload.

    The report is local-data only and safe in degraded provider mode.
    """
    if gems_limit < 1:
        raise ValueError("gems_limit must be >= 1")
    if queue_limit < 1:
        raise ValueError("queue_limit must be >= 1")
    if min_median < 0:
        raise ValueError("min_median must be >= 0")

    status = get_status_report()
    setup = run_setup_report()
    gems = run_hidden_gems(min_median=min_median, limit=gems_limit)
    queue = run_value_refresh_queue(limit=queue_limit, stale_days=30)
    health = run_collection_health()

    readiness = _as_dict(status.get("provider_readiness"))
    readiness_summary = _as_dict(readiness.get("summary"))
    setup_checklist = _as_dict(setup.get("first_run_checklist"))
    daily_use_actions = [
        str(item).strip()
        for item in _as_list(setup.get("daily_use_actions"))
        if str(item).strip()
    ]
    if not daily_use_actions:
        daily_use_actions = [
            str(item).strip()
            for item in _as_list(setup.get("next_steps"))
            if str(item).strip()
        ][:5]

    gem_rows: list[dict[str, object]] = []
    for raw in _as_list(gems.get("gems")):
        row = _as_dict(raw)
        if not row:
            continue
        gem_rows.append(
            {
                "discogs_release_id": row.get("discogs_release_id"),
                "artist": row.get("artist"),
                "title": row.get("title"),
                "year": row.get("year"),
                "market_median": row.get("market_median"),
                "market_currency": row.get("market_currency"),
                "num_for_sale": row.get("num_for_sale"),
                "gem_score": row.get("gem_score"),
                "reasons": row.get("reasons"),
            }
        )

    queue_rows: list[dict[str, object]] = []
    for raw in _as_list(queue.get("queue"))[:queue_limit]:
        row = _as_dict(raw)
        if not row:
            continue
        queue_rows.append(
            {
                "discogs_release_id": row.get("discogs_release_id"),
                "artist": row.get("artist"),
                "title": row.get("title"),
                "market_need_reason": row.get("market_need_reason"),
                "market_median": row.get("market_median"),
                "market_last_updated_at": row.get("market_last_updated_at"),
            }
        )

    highlights: list[dict[str, object]] = []
    onboarding_state = str(readiness_summary.get("onboarding_state") or "")
    if onboarding_state in {"needs_required_setup", "needs_discogs_token"}:
        highlights.append(
            {
                "kind": "setup",
                "title": "Finish Discogs setup",
                "message": "Discogs token is still required before daily collection workflows.",
                "command_hint": "dplayer setup",
            }
        )
    elif onboarding_state == "needs_initial_sync":
        highlights.append(
            {
                "kind": "sync",
                "title": "Run your first collection sync",
                "message": "Sync once to unlock spin, value, and discovery surfaces.",
                "command_hint": "dplayer sync",
            }
        )

    if gem_rows:
        top = gem_rows[0]
        highlights.append(
            {
                "kind": "discovery",
                "title": "Tonight's hidden gem",
                "message": "{} - {}{}".format(
                    str(top.get("artist") or "Unknown Artist"),
                    str(top.get("title") or "Unknown Title"),
                    (
                        f" ({int(top.get('year'))})"
                        if isinstance(top.get("year"), int)
                        else ""
                    ),
                ),
                "release_id": top.get("discogs_release_id"),
                "command_hint": "dplayer value gems --limit 10 --json",
            }
        )

    total_candidates = int(queue.get("total_candidates") or 0)
    if total_candidates > 0:
        highlights.append(
            {
                "kind": "value",
                "title": "Price refresh backlog",
                "message": (
                    f"{total_candidates} releases are queued for price refresh "
                    f"(missing={int(queue.get('missing_count') or 0)}, "
                    f"unpriced={int(queue.get('unpriced_count') or 0)}, "
                    f"stale={int(queue.get('stale_count') or 0)})."
                ),
                "command_hint": "dplayer value queue --limit 25 --stale-days 30",
            }
        )

    score = int(health.get("score") or 0)
    if score < 80:
        highlights.append(
            {
                "kind": "health",
                "title": "Collection health needs attention",
                "message": f"Health score is {score}/100. Check the largest gap buckets.",
                "command_hint": "dplayer health",
            }
        )

    return {
        "summary": {
            "release_count_active": int(status.get("release_count_active") or 0),
            "mapped_count": int(status.get("mapped_count") or 0),
            "unmatched_count": int(status.get("unmatched_count") or 0),
            "wantlist_count": int(status.get("wantlist_count") or 0),
            "market_value_last_updated": status.get("market_value_last_updated"),
            "last_sync_time": status.get("last_sync_time"),
            "last_spin_release_id": status.get("last_spin_release_id"),
            "onboarding_state": onboarding_state,
            "degraded_mode": bool(readiness_summary.get("degraded_mode")),
            "health_score": score,
            "hidden_gems_count": int(gems.get("count") or 0),
            "refresh_queue_count": total_candidates,
            "ready_for_daily_use": bool(setup_checklist.get("ready_for_daily_use")),
        },
        "provider_readiness_summary": readiness_summary,
        "highlights": highlights,
        "daily_use_actions": daily_use_actions,
        "top_hidden_gems": gem_rows,
        "refresh_queue_preview": queue_rows,
        "legacy_spotify_compatibility": {
            "status_report_has_spotify_capability": isinstance(
                status.get("spotify_capability"), dict
            ),
            "setup_report_has_spotify_block": isinstance(setup.get("spotify"), dict),
        },
    }

