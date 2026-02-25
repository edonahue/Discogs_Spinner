"""Detect likely duplicate releases and variant families in active collection."""

from __future__ import annotations

import re
from typing import Any

from discogs_player.use_cases.list_releases import run_list_releases

_NORMALIZE_SPACE_RE = re.compile(r"\s+")
_NORMALIZE_PUNCT_RE = re.compile(r"[^0-9a-z\s]")


def _normalize_text(value: object | None) -> str:
    text = str(value or "").casefold().strip()
    text = _NORMALIZE_PUNCT_RE.sub(" ", text)
    text = _NORMALIZE_SPACE_RE.sub(" ", text).strip()
    return text


def _as_year(value: object | None) -> int | None:
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            parsed = int(stripped)
            if parsed > 0:
                return parsed
    return None


def _as_currency(value: object | None) -> str:
    return str(value or "").strip()


def _as_float(value: object | None) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _as_int(value: object | None) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped and stripped.lstrip("-").isdigit():
            return int(stripped)
    return 0


def _clamp_score(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _median_coherence(items: list[dict[str, object]]) -> float:
    medians = [
        median
        for median in (_as_float(item.get("market_median")) for item in items)
        if isinstance(median, float)
    ]
    if len(medians) < 2:
        return 0.5

    mean_value = sum(medians) / len(medians)
    if mean_value <= 0.0:
        return 0.5

    spread = (max(medians) - min(medians)) / mean_value
    if spread <= 0.15:
        return 1.0
    if spread <= 0.35:
        return 0.8
    if spread <= 0.60:
        return 0.55
    return 0.3


def _score_duplicate_group(items: list[dict[str, object]]) -> float:
    release_count = len(items)
    if release_count < 2:
        return 0.0

    year_known_count = sum(
        1 for item in items if isinstance(_as_year(item.get("year")), int)
    )
    year_known_ratio = year_known_count / release_count if release_count else 0.0
    count_bonus = min(max(release_count - 2, 0) * 0.10, 0.24)
    coherence_bonus = 0.12 * _median_coherence(items)
    score = 0.58 + count_bonus + (0.10 * year_known_ratio) + coherence_bonus
    return _clamp_score(score)


def _score_variant_group(items: list[dict[str, object]]) -> float:
    release_count = len(items)
    if release_count < 2:
        return 0.0

    years = sorted(
        {
            year
            for year in (_as_year(item.get("year")) for item in items)
            if isinstance(year, int)
        }
    )
    if len(years) < 2:
        return 0.0
    year_span = years[-1] - years[0]
    if year_span <= 2:
        span_score = 1.0
    elif year_span <= 8:
        span_score = 0.8
    elif year_span <= 20:
        span_score = 0.6
    else:
        span_score = 0.45

    count_bonus = min(max(release_count - 2, 0) * 0.08, 0.24)
    coherence_bonus = 0.12 * _median_coherence(items)
    score = 0.42 + count_bonus + (0.22 * span_score) + coherence_bonus
    return _clamp_score(score)


def _weighted_confidence_score(groups: list[dict[str, object]]) -> float | None:
    weighted_total = 0.0
    total_weight = 0
    for group in groups:
        confidence = _as_float(group.get("confidence_score"))
        if confidence is None:
            continue
        weight = max(_as_int(group.get("release_count")), 1)
        weighted_total += confidence * weight
        total_weight += weight
    if total_weight <= 0:
        return None
    return _clamp_score(weighted_total / total_weight)


def _confidence_percent(score: float | None) -> int | None:
    if score is None:
        return None
    return int(round(_clamp_score(score) * 100))


def _item_sort_key(item: dict[str, object]) -> tuple[float, int]:
    median = _as_float(item.get("market_median"))
    release_id = _as_int(item.get("discogs_release_id"))
    if median is None:
        return (float("inf"), release_id)
    return (-median, release_id)


def _to_detector_item(item: dict[str, object]) -> dict[str, object]:
    return {
        "discogs_release_id": _as_int(item.get("discogs_release_id")),
        "artist": str(item.get("artist") or "Unknown Artist"),
        "title": str(item.get("title") or "Unknown Title"),
        "year": _as_year(item.get("year")),
        "market_median": _as_float(item.get("market_median")),
        "market_currency": _as_currency(item.get("market_currency")),
    }


def _build_duplicate_groups(
    releases: list[dict[str, object]],
    *,
    group_limit: int,
) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str, int | None], list[dict[str, object]]] = {}
    for item in releases:
        artist_norm = _normalize_text(item.get("artist"))
        title_norm = _normalize_text(item.get("title"))
        if not artist_norm or not title_norm:
            continue
        key = (artist_norm, title_norm, _as_year(item.get("year")))
        grouped.setdefault(key, []).append(_to_detector_item(item))

    groups: list[dict[str, object]] = []
    for items in grouped.values():
        if len(items) < 2:
            continue
        sorted_items = sorted(items, key=_item_sort_key)
        first = sorted_items[0]
        year = first.get("year")
        year_text = str(year) if isinstance(year, int) else "Unknown Year"
        group_label = f"{first['artist']} - {first['title']} ({year_text})"
        confidence_score = _score_duplicate_group(sorted_items)
        groups.append(
            {
                "group_label": group_label,
                "artist": first["artist"],
                "title": first["title"],
                "year": year,
                "release_count": len(sorted_items),
                "confidence_score": confidence_score,
                "confidence_percent": _confidence_percent(confidence_score),
                "items": sorted_items,
            }
        )

    groups.sort(
        key=lambda group: (
            -_as_int(group.get("release_count")),
            str(group.get("artist") or "").casefold(),
            str(group.get("title") or "").casefold(),
            str(group.get("year") or ""),
        )
    )
    return groups[:group_limit]


def _build_variant_groups(
    releases: list[dict[str, object]],
    *,
    group_limit: int,
) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[dict[str, object]]] = {}
    for item in releases:
        artist_norm = _normalize_text(item.get("artist"))
        title_norm = _normalize_text(item.get("title"))
        if not artist_norm or not title_norm:
            continue
        grouped.setdefault((artist_norm, title_norm), []).append(
            _to_detector_item(item)
        )

    groups: list[dict[str, object]] = []
    for items in grouped.values():
        if len(items) < 2:
            continue

        years = sorted(
            {
                year
                for year in (_as_year(item.get("year")) for item in items)
                if isinstance(year, int)
            }
        )
        if len(years) < 2:
            continue

        sorted_items = sorted(items, key=_item_sort_key)
        first = sorted_items[0]
        year_span = f"{years[0]}-{years[-1]}" if years else "Unknown"
        group_label = f"{first['artist']} - {first['title']} ({year_span})"
        confidence_score = _score_variant_group(sorted_items)
        groups.append(
            {
                "group_label": group_label,
                "artist": first["artist"],
                "title": first["title"],
                "year_span": year_span,
                "release_count": len(sorted_items),
                "confidence_score": confidence_score,
                "confidence_percent": _confidence_percent(confidence_score),
                "items": sorted_items,
            }
        )

    groups.sort(
        key=lambda group: (
            -_as_int(group.get("release_count")),
            str(group.get("artist") or "").casefold(),
            str(group.get("title") or "").casefold(),
        )
    )
    return groups[:group_limit]


def run_duplicate_variant_detector(
    *,
    group_limit: int = 8,
) -> dict[str, Any]:
    if group_limit < 1:
        raise ValueError("group_limit must be >= 1")

    releases = run_list_releases(limit=None, with_value=True)
    duplicate_groups = _build_duplicate_groups(releases, group_limit=int(group_limit))
    variant_groups = _build_variant_groups(releases, group_limit=int(group_limit))
    duplicate_confidence_score = _weighted_confidence_score(duplicate_groups)
    variant_confidence_score = _weighted_confidence_score(variant_groups)
    overall_confidence_score = _weighted_confidence_score(
        [*duplicate_groups, *variant_groups]
    )

    return {
        "group_limit": int(group_limit),
        "active_release_count": len(releases),
        "duplicate_group_count": len(duplicate_groups),
        "duplicate_release_count": sum(
            _as_int(group.get("release_count")) for group in duplicate_groups
        ),
        "duplicate_confidence_score": duplicate_confidence_score,
        "duplicate_confidence_percent": _confidence_percent(duplicate_confidence_score),
        "variant_group_count": len(variant_groups),
        "variant_release_count": sum(
            _as_int(group.get("release_count")) for group in variant_groups
        ),
        "variant_confidence_score": variant_confidence_score,
        "variant_confidence_percent": _confidence_percent(variant_confidence_score),
        "confidence_score": overall_confidence_score,
        "confidence_percent": _confidence_percent(overall_confidence_score),
        "duplicate_groups": duplicate_groups,
        "variant_groups": variant_groups,
    }
