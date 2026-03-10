"""Tests for the analytics and value export use-cases."""

from __future__ import annotations

import csv
from unittest.mock import MagicMock

import pytest

from discogs_player.use_cases import export as export_module
from discogs_player.use_cases.export import run_export_analytics, run_export_value


# ---------------------------------------------------------------------------
# Shared mock data
# ---------------------------------------------------------------------------

_ANALYTICS_REPORT = {
    "release_count_active": 50,
    "mapped_count": 40,
    "unmatched_count": 10,
    "top_limit": 5,
    "by_release_year": [{"year": 1990, "count": 3}, {"year": 2000, "count": 5}],
    "acquisition_timeline": [{"year": 2025, "count": 10}],
    "top_genres": [{"genre": "Rock", "count": 20}, {"genre": "Jazz", "count": 8}],
    "top_styles": [{"style": "Grunge", "count": 12}],
    "top_artists": [{"artist": "Nirvana", "count": 4}],
}

_VALUE_SUMMARY = {
    "active_release_count": 100,
    "priced_release_count": 80,
    "unpriced_release_count": 20,
    "total_lowest": 500.0,
    "total_median": 1000.0,
    "total_highest": 2000.0,
    "market_value_last_updated": "2026-03-09",
    "currency_counts": [{"currency": "USD", "count": 75}, {"currency": "EUR", "count": 5}],
}


# ---------------------------------------------------------------------------
# run_export_analytics — CSV
# ---------------------------------------------------------------------------

def test_export_analytics_csv(monkeypatch, tmp_path):
    monkeypatch.setattr(export_module, "run_collection_analytics", MagicMock(return_value=_ANALYTICS_REPORT))

    output = tmp_path / "analytics.csv"
    result = run_export_analytics(output_path=str(output), export_format="csv", limit=5)

    assert result["ok"] is True
    assert result["export_format"] == "csv"
    assert result["release_count_active"] == 50
    assert output.exists()

    with output.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))

    # Header row
    assert rows[0] == ["section", "key", "count"]

    # Check some data rows
    sections = {row[0] for row in rows[1:]}
    assert "release_year" in sections
    assert "genre" in sections
    assert "style" in sections
    assert "artist" in sections
    assert "acquisition_year" in sections


def test_export_analytics_csv_content(monkeypatch, tmp_path):
    monkeypatch.setattr(export_module, "run_collection_analytics", MagicMock(return_value=_ANALYTICS_REPORT))

    output = tmp_path / "analytics.csv"
    run_export_analytics(output_path=str(output), export_format="csv")

    with output.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    genre_rows = [r for r in rows if r["section"] == "genre"]
    assert len(genre_rows) == 2
    assert genre_rows[0]["key"] == "Rock"
    assert genre_rows[0]["count"] == "20"


# ---------------------------------------------------------------------------
# run_export_analytics — Markdown
# ---------------------------------------------------------------------------

def test_export_analytics_markdown(monkeypatch, tmp_path):
    monkeypatch.setattr(export_module, "run_collection_analytics", MagicMock(return_value=_ANALYTICS_REPORT))

    output = tmp_path / "analytics.md"
    result = run_export_analytics(output_path=str(output), export_format="markdown")

    assert result["ok"] is True
    assert result["export_format"] == "markdown"
    assert output.exists()

    content = output.read_text(encoding="utf-8")
    assert "# Collection Analytics" in content
    assert "Active releases" in content
    assert "50" in content
    assert "Rock" in content
    assert "Nirvana" in content


def test_export_analytics_markdown_alias(monkeypatch, tmp_path):
    """'md' is accepted as an alias for 'markdown'."""
    monkeypatch.setattr(export_module, "run_collection_analytics", MagicMock(return_value=_ANALYTICS_REPORT))

    output = tmp_path / "analytics.md"
    result = run_export_analytics(output_path=str(output), export_format="md")
    assert result["export_format"] == "markdown"


# ---------------------------------------------------------------------------
# run_export_analytics — validation
# ---------------------------------------------------------------------------

def test_export_analytics_rejects_invalid_format(tmp_path):
    output = tmp_path / "analytics.xml"
    with pytest.raises(ValueError, match="format must be"):
        run_export_analytics(output_path=str(output), export_format="xml")


def test_export_analytics_rejects_invalid_limit(tmp_path):
    output = tmp_path / "analytics.csv"
    with pytest.raises(ValueError, match="limit must be >= 1"):
        run_export_analytics(output_path=str(output), limit=0)


def test_export_analytics_rejects_directory_output(monkeypatch, tmp_path):
    monkeypatch.setattr(export_module, "run_collection_analytics", MagicMock(return_value=_ANALYTICS_REPORT))
    with pytest.raises(ValueError, match="directory"):
        run_export_analytics(output_path=str(tmp_path))


# ---------------------------------------------------------------------------
# run_export_value — Markdown
# ---------------------------------------------------------------------------

def test_export_value_markdown(monkeypatch, tmp_path):
    monkeypatch.setattr(export_module, "run_market_value_status", MagicMock(return_value=_VALUE_SUMMARY))

    output = tmp_path / "value.md"
    result = run_export_value(output_path=str(output), export_format="markdown")

    assert result["ok"] is True
    assert result["export_format"] == "markdown"
    assert result["active_release_count"] == 100
    assert result["priced_release_count"] == 80
    assert output.exists()

    content = output.read_text(encoding="utf-8")
    assert "# Collection Market Value Summary" in content
    assert "2026-03-09" in content
    assert "1,000.00" in content
    assert "USD" in content
    assert "EUR" in content


def test_export_value_rejects_invalid_format(tmp_path):
    output = tmp_path / "value.csv"
    with pytest.raises(ValueError, match="format must be"):
        run_export_value(output_path=str(output), export_format="csv")


def test_export_value_rejects_directory_output(monkeypatch, tmp_path):
    monkeypatch.setattr(export_module, "run_market_value_status", MagicMock(return_value=_VALUE_SUMMARY))
    with pytest.raises(ValueError, match="directory"):
        run_export_value(output_path=str(tmp_path))


def test_export_value_creates_parent_dirs(monkeypatch, tmp_path):
    monkeypatch.setattr(export_module, "run_market_value_status", MagicMock(return_value=_VALUE_SUMMARY))

    nested = tmp_path / "deep" / "nested" / "value.md"
    result = run_export_value(output_path=str(nested))
    assert result["ok"] is True
    assert nested.exists()
