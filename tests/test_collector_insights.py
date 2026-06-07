from __future__ import annotations

import pytest

from discogs_player.use_cases import collector_insights


def test_run_collector_insights_builds_expected_sections(monkeypatch):
    monkeypatch.setattr(
        collector_insights,
        "get_status_report",
        lambda: {
            "release_count_active": 120,
            "mapped_count": 80,
            "unmatched_count": 40,
            "wantlist_count": 12,
            "market_value_last_updated": "2026-05-01T00:00:00Z",
            "last_sync_time": "2026-05-02T00:00:00Z",
            "last_spin_release_id": 55,
            "provider_readiness": {
                "summary": {
                    "onboarding_state": "core_ready_optional_pending",
                    "degraded_mode": True,
                }
            },
            "spotify_capability": {"configured": False},
        },
    )
    monkeypatch.setattr(
        collector_insights,
        "run_setup_report",
        lambda: {
            "first_run_checklist": {"ready_for_daily_use": True},
            "daily_use_actions": ["Run dplayer spin", "Run dplayer value gems"],
            "spotify": {"configured": False},
        },
    )
    monkeypatch.setattr(
        collector_insights,
        "run_hidden_gems",
        lambda **kwargs: {
            "count": 1,
            "gems": [
                {
                    "discogs_release_id": 9,
                    "artist": "Broadcast",
                    "title": "Tender Buttons",
                    "year": 2005,
                    "market_median": 55.0,
                    "market_currency": "USD",
                    "num_for_sale": 1,
                    "gem_score": 80.0,
                    "reasons": ["scarce-now", "high-value"],
                }
            ],
            **kwargs,
        },
    )
    monkeypatch.setattr(
        collector_insights,
        "run_value_refresh_queue",
        lambda **kwargs: {
            "total_candidates": 3,
            "missing_count": 1,
            "unpriced_count": 1,
            "stale_count": 1,
            "queue": [
                {
                    "discogs_release_id": 10,
                    "artist": "A",
                    "title": "B",
                    "market_need_reason": "missing",
                    "market_median": None,
                }
            ],
            **kwargs,
        },
    )
    monkeypatch.setattr(
        collector_insights,
        "run_collection_health",
        lambda: {"score": 72, "buckets": [], "total_active": 120},
    )

    result = collector_insights.run_collector_insights(
        gems_limit=3, queue_limit=5, min_median=30.0
    )

    summary = result["summary"]
    assert summary["release_count_active"] == 120
    assert summary["health_score"] == 72
    assert summary["hidden_gems_count"] == 1
    assert summary["refresh_queue_count"] == 3
    assert summary["onboarding_state"] == "core_ready_optional_pending"
    assert summary["ready_for_daily_use"] is True

    assert result["daily_use_actions"] == ["Run dplayer spin", "Run dplayer value gems"]
    assert result["top_hidden_gems"][0]["discogs_release_id"] == 9
    assert result["refresh_queue_preview"][0]["discogs_release_id"] == 10
    assert result["legacy_spotify_compatibility"]["status_report_has_spotify_capability"] is True
    assert result["legacy_spotify_compatibility"]["setup_report_has_spotify_block"] is True
    assert any(item["kind"] == "discovery" for item in result["highlights"])
    assert any(item["kind"] == "health" for item in result["highlights"])


def test_run_collector_insights_validates_inputs():
    with pytest.raises(ValueError):
        collector_insights.run_collector_insights(gems_limit=0)
    with pytest.raises(ValueError):
        collector_insights.run_collector_insights(queue_limit=0)
    with pytest.raises(ValueError):
        collector_insights.run_collector_insights(min_median=-1.0)

