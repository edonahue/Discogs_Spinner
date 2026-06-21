"""Surface high-value + scarce releases as 'Hidden Gems'.

Goes beyond Discogs.com's raw low/median/high numbers by combining market
value with current scarcity (num_for_sale) and community demand (want vs.
have) to rank releases the collector may not realize are quietly valuable.
"""

from __future__ import annotations

from discogs_player.data.db import get_connection
from discogs_player.data.repo import query_hidden_gems
from discogs_player.use_cases._coerce import to_optional_float as _as_float
from discogs_player.use_cases._coerce import to_optional_int as _as_int

_DEFAULT_MIN_MEDIAN = 25.0
_DEFAULT_LIMIT = 25


def _scarcity(num_for_sale: int | None) -> float:
    if num_for_sale is None or num_for_sale < 0:
        return 0.1
    return 1.0 / (1.0 + float(num_for_sale))


def _gem_score(
    *,
    median: float,
    num_for_sale: int | None,
    community_want: int | None,
    community_have: int | None,
) -> float:
    scarcity = _scarcity(num_for_sale)
    have = max(1, int(community_have or 0))
    want = int(community_want or 0)
    demand_factor = 1.0 + 0.1 * (want / have)
    return median * scarcity * demand_factor


def _reason_tags(
    *,
    median: float,
    year: int | None,
    num_for_sale: int | None,
    community_have: int | None,
    community_want: int | None,
) -> list[str]:
    tags: list[str] = []
    if num_for_sale is not None and num_for_sale <= 1:
        tags.append("scarce-now")
    if median >= 50.0:
        tags.append("high-value")
    if (
        year is not None
        and year >= 2000
        and median >= 50.0
    ):
        tags.append("surprising")
    if (
        community_want is not None
        and community_have is not None
        and community_have > 0
        and community_want > community_have
    ):
        tags.append("community-hot")
    return tags


def run_hidden_gems(
    *,
    min_median: float = _DEFAULT_MIN_MEDIAN,
    limit: int = _DEFAULT_LIMIT,
) -> dict[str, object]:
    if min_median < 0:
        raise ValueError("min_median must be >= 0")
    if limit < 1:
        raise ValueError("limit must be >= 1")

    conn = get_connection()
    try:
        rows = query_hidden_gems(conn, min_median=min_median, limit=limit)
    finally:
        conn.close()

    enriched: list[dict[str, object]] = []
    for row in rows:
        median = _as_float(row.get("market_median"))
        if median is None:
            continue
        num_for_sale = _as_int(row.get("num_for_sale"))
        community_have = _as_int(row.get("community_have"))
        community_want = _as_int(row.get("community_want"))
        year = _as_int(row.get("year"))

        score = _gem_score(
            median=median,
            num_for_sale=num_for_sale,
            community_want=community_want,
            community_have=community_have,
        )
        reasons = _reason_tags(
            median=median,
            year=year,
            num_for_sale=num_for_sale,
            community_have=community_have,
            community_want=community_want,
        )

        enriched.append(
            {
                **row,
                "gem_score": round(score, 4),
                "reasons": reasons,
            }
        )

    enriched.sort(key=lambda item: _as_float(item.get("gem_score")) or 0.0, reverse=True)

    return {
        "ok": True,
        "min_median": float(min_median),
        "limit": int(limit),
        "count": len(enriched),
        "gems": enriched,
    }
