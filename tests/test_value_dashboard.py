from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from discogs_player.use_cases import value_dashboard


def test_run_market_value_dashboard_aggregates_data(monkeypatch):
    mock_status = MagicMock(
        return_value={
            "active_release_count": 100,
            "priced_release_count": 80,
            "total_lowest": 1000.0,
            "total_median": 2000.0,
            "total_highest": 3000.0,
            "currency_counts": [{"currency": "USD", "count": 80}],
            "market_value_last_updated": "2026-02-08",
        }
    )
    monkeypatch.setattr(value_dashboard, "run_market_value_status", mock_status)

    mock_examples = MagicMock(
        return_value={
            "high_priced": [{"discogs_release_id": 1, "market_median": 100.0}],
            "low_priced": [{"discogs_release_id": 2, "market_median": 5.0}],
        }
    )
    monkeypatch.setattr(value_dashboard, "run_market_value_examples", mock_examples)

    mock_trend = MagicMock(
        return_value={
            "snapshot_count": 5,
            "window_start": "2026-01-01",
            "window_end": "2026-02-01",
            "points": [{"captured_at": "2026-02-01", "total_median": 2000.0}],
        }
    )
    monkeypatch.setattr(value_dashboard, "run_market_value_trend", mock_trend)

    mock_detector = MagicMock(
        return_value={
            "duplicate_group_count": 1,
            "variant_group_count": 0,
        }
    )
    monkeypatch.setattr(
        value_dashboard, "run_duplicate_variant_detector", mock_detector
    )

    result = value_dashboard.run_market_value_dashboard()

    assert result["summary"]["active_release_count"] == 100
    assert result["coverage"]["ratio"] == 0.8
    assert len(result["top_priced"]) == 1
    assert len(result["bottom_priced"]) == 1
    assert result["trend"]["snapshot_count"] == 5
    assert result["detector"]["duplicate_group_count"] == 1
    assert len(result["value_bands"]) == 3
    assert result["value_bands"][1]["amount"] == 2000.0  # Median


def test_run_market_value_dashboard_validates_limits():
    with pytest.raises(ValueError):
        value_dashboard.run_market_value_dashboard(top_limit=0)
