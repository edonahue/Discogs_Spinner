"""Analytics and value summary export use-cases.

Exports collection analytics and market-value dashboard data to portable
formats (CSV, Markdown) for sharing outside the app.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import cast

from discogs_player.use_cases.collection_analytics import run_collection_analytics
from discogs_player.use_cases.value_status import run_market_value_status


def _normalize_format(raw: str) -> str:
    fmt = raw.strip().lower()
    if fmt not in {"csv", "markdown", "md"}:
        raise ValueError("format must be 'csv' or 'markdown'")
    return "markdown" if fmt == "md" else fmt


def _as_rows(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []

    rows: list[dict[str, object]] = []
    for item in value:
        if isinstance(item, dict):
            rows.append(cast(dict[str, object], item))
    return rows


def _to_int(value: object, *, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if text:
            try:
                return int(text)
            except ValueError:
                return default
    return default


def _to_float(value: object, *, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if text:
            try:
                return float(text)
            except ValueError:
                return default
    return default


# ---------------------------------------------------------------------------
# Collection analytics export
# ---------------------------------------------------------------------------

def _analytics_to_csv(report: dict[str, object]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)

    writer.writerow(["section", "key", "count"])

    for row in _as_rows(report.get("by_release_year")):
        writer.writerow(["release_year", str(row.get("year") or ""), str(row.get("count") or 0)])

    for row in _as_rows(report.get("top_genres")):
        writer.writerow(["genre", str(row.get("genre") or ""), str(row.get("count") or 0)])

    for row in _as_rows(report.get("top_styles")):
        writer.writerow(["style", str(row.get("style") or ""), str(row.get("count") or 0)])

    for row in _as_rows(report.get("top_artists")):
        writer.writerow(["artist", str(row.get("artist") or ""), str(row.get("count") or 0)])

    for row in _as_rows(report.get("acquisition_timeline")):
        writer.writerow(["acquisition_year", str(row.get("year") or ""), str(row.get("count") or 0)])

    return buf.getvalue()


def _analytics_to_markdown(report: dict[str, object]) -> str:
    active = _to_int(report.get("release_count_active"))
    mapped = _to_int(report.get("mapped_count"))
    unmatched = _to_int(report.get("unmatched_count"))
    mapping_rate = (mapped / active * 100.0) if active > 0 else 0.0

    lines: list[str] = [
        "# Collection Analytics",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| Active releases | {active} |",
        f"| Mapped (Spotify) | {mapped} |",
        f"| Unmatched | {unmatched} |",
        f"| Mapping rate | {mapping_rate:.1f}% |",
        "",
    ]

    def _section_table(title: str, rows: list[dict[str, object]], key_field: str, key_header: str) -> list[str]:
        out = [f"## {title}", "", f"| {key_header} | Count |", f"|{''.join(['-'] * (len(key_header) + 2))}|-------|"]
        for row in rows:
            out.append(f"| {row.get(key_field) or ''} | {row.get('count') or 0} |")
        out.append("")
        return out

    lines.extend(_section_table("Top Genres", _as_rows(report.get("top_genres")), "genre", "Genre"))
    lines.extend(_section_table("Top Styles", _as_rows(report.get("top_styles")), "style", "Style"))
    lines.extend(_section_table("Top Artists", _as_rows(report.get("top_artists")), "artist", "Artist"))
    lines.extend(_section_table("By Release Year", _as_rows(report.get("by_release_year")), "year", "Year"))
    lines.extend(_section_table("Acquisition Timeline", _as_rows(report.get("acquisition_timeline")), "year", "Year"))

    return "\n".join(lines) + "\n"


def run_export_analytics(
    *,
    output_path: str,
    export_format: str = "csv",
    limit: int = 20,
) -> dict[str, object]:
    """Export collection analytics (genres, styles, artists, years) to file."""
    normalized_format = _normalize_format(export_format)
    if limit < 1:
        raise ValueError("limit must be >= 1")

    output = Path(output_path).expanduser()
    if output.exists() and output.is_dir():
        raise ValueError(f"Output path is a directory: {output}")

    report = run_collection_analytics(limit=limit)

    if normalized_format == "csv":
        content = _analytics_to_csv(report)
    else:
        content = _analytics_to_markdown(report)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")

    return {
        "ok": True,
        "export_format": normalized_format,
        "output_path": str(output),
        "release_count_active": _to_int(report.get("release_count_active")),
    }


# ---------------------------------------------------------------------------
# Value summary export
# ---------------------------------------------------------------------------

def _value_to_markdown(summary: dict[str, object]) -> str:
    active = _to_int(summary.get("active_release_count"))
    priced = _to_int(summary.get("priced_release_count"))
    unpriced = _to_int(summary.get("unpriced_release_count"))
    total_low = _to_float(summary.get("total_lowest"))
    total_med = _to_float(summary.get("total_median"))
    total_high = _to_float(summary.get("total_highest"))
    coverage = (priced / active * 100.0) if active > 0 else 0.0
    updated = str(summary.get("market_value_last_updated") or "unknown")

    lines: list[str] = [
        "# Collection Market Value Summary",
        "",
        f"_Last updated: {updated}_",
        "",
        "## Overview",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| Active releases | {active} |",
        f"| Priced releases | {priced} |",
        f"| Unpriced releases | {unpriced} |",
        f"| Coverage | {coverage:.1f}% |",
        "",
        "## Value Totals",
        "",
        "| Band | Total |",
        "|------|-------|",
        f"| Low | ${total_low:,.2f} |",
        f"| Median | ${total_med:,.2f} |",
        f"| High | ${total_high:,.2f} |",
        "",
    ]

    currency_counts = _as_rows(summary.get("currency_counts"))
    if currency_counts:
        lines.extend([
            "## Currency Mix",
            "",
            "| Currency | Count |",
            "|----------|-------|",
        ])
        for row in currency_counts:
            lines.append(f"| {row.get('currency') or 'Unknown'} | {row.get('count') or 0} |")
        lines.append("")

    return "\n".join(lines) + "\n"


def run_export_value(
    *,
    output_path: str,
    export_format: str = "markdown",
) -> dict[str, object]:
    """Export market value summary to a shareable Markdown file."""
    fmt = export_format.strip().lower()
    if fmt not in {"markdown", "md"}:
        raise ValueError("format must be 'markdown'")
    normalized_format = "markdown"

    output = Path(output_path).expanduser()
    if output.exists() and output.is_dir():
        raise ValueError(f"Output path is a directory: {output}")

    summary = run_market_value_status()
    content = _value_to_markdown(summary)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")

    return {
        "ok": True,
        "export_format": normalized_format,
        "output_path": str(output),
        "active_release_count": _to_int(summary.get("active_release_count")),
        "priced_release_count": _to_int(summary.get("priced_release_count")),
    }
