"""Assemble market value dashboard data for GUI rendering."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from discogs_player.use_cases.duplicate_variant_detector import (
    run_duplicate_variant_detector,
)
from discogs_player.use_cases.value_examples import run_market_value_examples
from discogs_player.use_cases.value_status import run_market_value_status
from discogs_player.use_cases.value_trend import run_market_value_trend


def _as_float(value: object | None) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def _as_int(value: object | None) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0


def _as_str(value: object | None) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _parse_top_rows(value: object, *, limit: int) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, object]] = []
    for item in value[:limit]:
        if isinstance(item, dict):
            rows.append(dict(item))
    return rows


def _derive_value_bands(summary: dict[str, object]) -> list[dict[str, object]]:
    low_total = _as_float(summary.get("total_lowest"))
    median_total = _as_float(summary.get("total_median"))
    high_total = _as_float(summary.get("total_highest"))
    max_total = max(low_total, median_total, high_total, 0.0)

    def _ratio(amount: float) -> float:
        if max_total <= 0.0:
            return 0.0
        return max(0.0, min(1.0, amount / max_total))

    return [
        {"key": "low", "label": "Low", "amount": low_total, "ratio": _ratio(low_total)},
        {
            "key": "median",
            "label": "Median",
            "amount": median_total,
            "ratio": _ratio(median_total),
        },
        {
            "key": "high",
            "label": "High",
            "amount": high_total,
            "ratio": _ratio(high_total),
        },
    ]


def _derive_currency_mix(summary: dict[str, object]) -> list[dict[str, object]]:
    priced_count = max(_as_int(summary.get("priced_release_count")), 0)
    raw_rows = summary.get("currency_counts")
    if not isinstance(raw_rows, list):
        return []

    rows: list[dict[str, object]] = []
    for row in raw_rows:
        if not isinstance(row, dict):
            continue
        currency = _as_str(row.get("currency")) or "Unknown"
        count = max(_as_int(row.get("count")), 0)
        ratio = (count / priced_count) if priced_count else 0.0
        rows.append(
            {
                "currency": currency,
                "count": count,
                "ratio": max(0.0, min(1.0, ratio)),
            }
        )
    return rows


def _derive_trend_rows(trend_report: dict[str, object]) -> list[dict[str, object]]:
    raw_points = trend_report.get("points")
    if not isinstance(raw_points, list):
        return []

    points: list[dict[str, object]] = []
    max_median = 0.0
    for item in raw_points:
        if not isinstance(item, dict):
            continue
        median_total = _as_float(item.get("total_median"))
        max_median = max(max_median, median_total)
        points.append(
            {
                "captured_at": _as_str(item.get("captured_at")),
                "total_median": median_total,
            }
        )

    for item in points:
        captured_at = _as_str(item.get("captured_at"))
        label = (
            captured_at[:10] if len(captured_at) >= 10 else (captured_at or "(unknown)")
        )
        item["label"] = label
        item["ratio"] = (
            max(0.0, min(1.0, _as_float(item.get("total_median")) / max_median))
            if max_median > 0.0
            else 0.0
        )
    return points


def run_market_value_dashboard(
    *,
    top_limit: int = 10,
    bottom_limit: int = 2,
    trend_limit: int = 12,
    detector_limit: int = 8,
) -> dict[str, object]:
    if top_limit < 1:
        raise ValueError("top_limit must be >= 1")
    if bottom_limit < 1:
        raise ValueError("bottom_limit must be >= 1")
    if trend_limit < 1:
        raise ValueError("trend_limit must be >= 1")
    if detector_limit < 1:
        raise ValueError("detector_limit must be >= 1")

    normalized_top_limit = int(top_limit)
    normalized_bottom_limit = int(bottom_limit)
    normalized_trend_limit = int(trend_limit)
    normalized_detector_limit = int(detector_limit)
    examples_limit = max(normalized_top_limit, normalized_bottom_limit)

    with ThreadPoolExecutor(
        max_workers=4, thread_name_prefix="value-dashboard"
    ) as executor:
        summary_future = executor.submit(run_market_value_status)
        examples_future = executor.submit(
            run_market_value_examples, limit=examples_limit
        )
        trend_future = executor.submit(
            run_market_value_trend, limit=normalized_trend_limit
        )
        detector_future = executor.submit(
            run_duplicate_variant_detector,
            group_limit=normalized_detector_limit,
        )

        summary = dict(summary_future.result())
        examples = dict(examples_future.result())
        trend_report = dict(trend_future.result())
        detector_report = dict(detector_future.result())

    active_release_count = max(_as_int(summary.get("active_release_count")), 0)
    priced_release_count = max(_as_int(summary.get("priced_release_count")), 0)
    coverage_ratio = (
        (priced_release_count / active_release_count) if active_release_count else 0.0
    )

    top_priced = _parse_top_rows(
        examples.get("high_priced"), limit=normalized_top_limit
    )
    bottom_priced = _parse_top_rows(
        examples.get("low_priced"), limit=normalized_bottom_limit
    )
    currency_mix = _derive_currency_mix(summary)

    return {
        "summary": summary,
        "top_limit": normalized_top_limit,
        "bottom_limit": normalized_bottom_limit,
        "trend_limit": normalized_trend_limit,
        "detector_limit": normalized_detector_limit,
        "top_priced": top_priced,
        "bottom_priced": bottom_priced,
        "coverage": {
            "active_release_count": active_release_count,
            "priced_release_count": priced_release_count,
            "unpriced_release_count": max(
                active_release_count - priced_release_count, 0
            ),
            "ratio": max(0.0, min(1.0, coverage_ratio)),
        },
        "value_bands": _derive_value_bands(summary),
        "currency_mix": currency_mix,
        "trend": {
            "snapshot_count": max(_as_int(trend_report.get("snapshot_count")), 0),
            "window_start": trend_report.get("window_start"),
            "window_end": trend_report.get("window_end"),
            "window_delta_total_median": trend_report.get("window_delta_total_median"),
            "window_delta_total_median_percent": trend_report.get(
                "window_delta_total_median_percent"
            ),
            "points": _derive_trend_rows(trend_report),
        },
        "detector": detector_report,
    }
