"""Shared UI formatting utilities for discogs_player."""

from __future__ import annotations

from typing import Any


def format_price(value: object, currency: str) -> str:
    """Format a price value with currency symbol."""
    if not isinstance(value, (int, float)):
        return "n/a"

    amount = f"{float(value):,.2f}"
    normalized_currency = currency.strip().upper()
    if normalized_currency in {"", "$", "USD", "US$"}:
        return f"${amount}"

    return f"{normalized_currency} {amount}"


def format_market_summary(item: dict[str, Any]) -> str:
    """Format a summary string of lowest, median, and highest market prices."""
    lowest = item.get("market_lowest")
    median = item.get("market_median")
    highest = item.get("market_highest")
    currency = str(item.get("market_currency") or "").strip().upper()

    has_any_price = any(
        isinstance(value, (int, float)) for value in (lowest, median, highest)
    )
    if not has_any_price:
        return "Market: n/a"

    def _fmt(val: object) -> str:
        return format_price(val, currency)

    parts = [
        f"L {_fmt(lowest)}",
        f"M {_fmt(median)}",
        f"H {_fmt(highest)}",
    ]
    return f"Market: {' • '.join(parts)}"


def format_market_metrics(item: dict[str, Any]) -> str:
    """Format market metrics like spread, midpoint, and last updated date."""
    lowest = item.get("market_lowest")
    median = item.get("market_median")
    highest = item.get("market_highest")
    currency = str(item.get("market_currency") or "").strip().upper()
    market_updated = str(item.get("market_last_updated_at") or "").strip()

    spread: float | None = None
    midpoint: float | None = None
    if isinstance(lowest, (int, float)) and isinstance(highest, (int, float)):
        spread = float(highest) - float(lowest)
        midpoint = (float(highest) + float(lowest)) / 2.0
    elif isinstance(median, (int, float)):
        midpoint = float(median)

    parts: list[str] = []
    if isinstance(spread, float):
        parts.append(f"Spread {format_price(spread, currency)}")
    if isinstance(midpoint, float):
        parts.append(f"Midpoint {format_price(midpoint, currency)}")
    if market_updated:
        # If market_updated is isoformat, slice to YYYY-MM-DD
        parts.append(f"Updated {market_updated[:10]}")

    if not parts:
        return "Metrics: n/a"
    return f"Metrics: {' • '.join(parts)}"


def format_community_stats(item: dict[str, Any]) -> str:
    """Format community stats like ratings, have/want counts, and for sale count."""
    num_for_sale = item.get("num_for_sale")
    community_have = item.get("community_have")
    community_want = item.get("community_want")
    rating_count = item.get("rating_count")
    rating_average = item.get("rating_average")

    parts: list[str] = []

    if isinstance(rating_average, (int, float)):
        rating_str = f"Rating {float(rating_average):.2f}"
        if isinstance(rating_count, int):
            rating_str += f" ({rating_count})"
        parts.append(rating_str)

    if isinstance(community_have, int) and isinstance(community_want, int):
        parts.append(f"Have {community_have} / Want {community_want}")

    if isinstance(num_for_sale, int):
        parts.append(f"For Sale {num_for_sale}")

    if not parts:
        return "Stats: n/a"

    return " • ".join(parts)


def format_discogs_date(value: object) -> str:
    """Format a date string (YYYY-MM-DD...) to YYYY-MM-DD or return 'n/a'."""
    text = str(value or "").strip()
    if not text:
        return "n/a"
    return text[:10]


def format_discogs_terms(value: object) -> str:
    """Format a list of strings (e.g. genres/styles) into a comma-separated string."""
    if not isinstance(value, list):
        return "n/a"
    terms = [str(item).strip() for item in value if str(item).strip()]
    if not terms:
        return "n/a"
    return ", ".join(terms)


def format_tracklist_meta_text(item: dict[str, Any]) -> str:
    """Format tracklist metadata summary."""
    has_cache = bool(item.get("has_cached_tracklist"))
    track_count = int(item.get("track_count") or 0)
    audio_track_count = int(item.get("audio_track_count") or 0)
    refreshed = format_discogs_date(item.get("tracklist_last_refreshed_at"))

    if not has_cache:
        # Fallback logic might differ slightly per widget, but standardizing here:
        # Original AlbumDetail logic: "Tracklist cache: not available yet."
        # Original WantlistDetail logic: "Tracklist cache: none"
        # We'll use the more descriptive one:
        if track_count <= 0:
            return "Tracklist cache: none"
        return "Tracklist cache: not fully cached"

    parts = [f"{audio_track_count}/{track_count} audio tracks"]
    if refreshed != "n/a":
        parts.append(f"refreshed {refreshed}")
    return f"Tracklist cache: {' • '.join(parts)}"


def format_tracklist_line(track: dict[str, Any]) -> str:
    """Format a single track line for display."""
    if not isinstance(track, dict):
        return ""

    position = str(track.get("position") or "").strip()
    title = str(track.get("title") or "").strip() or "(untitled)"
    duration = str(track.get("duration") or "").strip()
    row_type = str(track.get("type") or "").strip().lower()
    seq = track.get("seq")

    if not position and isinstance(seq, int):
        position = str(seq)

    if row_type and row_type != "track":
        return f"[{row_type}] {title}"

    # Standardize on the cleaner format from WantlistDetail or AlbumDetail
    # AlbumDetail: uses bullet if no position
    # WantlistDetail: just uses title if no position

    # Using AlbumDetail's slightly richer logic:
    left = position if position else "•"
    if duration:
        return f"{left} {title} ({duration})"
    return f"{left} {title}"


def format_tracklist_body_text(item: dict[str, Any]) -> str:
    """Format the full tracklist body text."""
    tracks_raw = item.get("tracks")
    tracks = (
        [row for row in tracks_raw if isinstance(row, dict)]
        if isinstance(tracks_raw, list)
        else []
    )

    if not tracks:
        has_cache = bool(item.get("has_cached_tracklist"))
        if has_cache:
            return "No tracks found in cached release details."
        return "No cached tracklist yet. Run refresh to populate."

    lines = [format_tracklist_line(track) for track in tracks]
    # Filter out empty lines if format_tracklist_line returns empty
    return "\n".join(line for line in lines if line)
