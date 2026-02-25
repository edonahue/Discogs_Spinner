from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from discogs_player.use_cases import duplicate_variant_detector


def _item(
    release_id: int,
    artist: str,
    title: str,
    year: int | None = 2000,
    median: float | None = 10.0,
) -> dict[str, object]:
    return {
        "discogs_release_id": release_id,
        "artist": artist,
        "title": title,
        "year": year,
        "market_median": median,
        "market_currency": "USD",
    }


def test_run_duplicate_variant_detector_groups_duplicates(monkeypatch):
    mock_run_list = MagicMock(
        return_value=[
            _item(1, "Artist A", "Title X", 2000, 10.0),
            _item(2, "Artist A", "Title X", 2000, 11.0),
            _item(3, "Artist B", "Title Y", 2001, 20.0),
        ]
    )
    monkeypatch.setattr(duplicate_variant_detector, "run_list_releases", mock_run_list)

    result = duplicate_variant_detector.run_duplicate_variant_detector(group_limit=5)

    assert result["active_release_count"] == 3
    assert result["duplicate_group_count"] == 1

    group = result["duplicate_groups"][0]
    assert group["artist"] == "Artist A"
    assert group["title"] == "Title X"
    assert group["release_count"] == 2
    assert len(group["items"]) == 2
    assert {item["discogs_release_id"] for item in group["items"]} == {1, 2}


def test_run_duplicate_variant_detector_groups_variants(monkeypatch):
    mock_run_list = MagicMock(
        return_value=[
            _item(10, "Artist V", "Album Z", 1990, 5.0),
            _item(11, "Artist V", "Album Z", 2010, 8.0),  # Different year -> variant
            _item(12, "Artist V", "Album Z", 2020, 12.0),
        ]
    )
    monkeypatch.setattr(duplicate_variant_detector, "run_list_releases", mock_run_list)

    result = duplicate_variant_detector.run_duplicate_variant_detector(group_limit=5)

    assert result["variant_group_count"] == 1

    group = result["variant_groups"][0]
    assert group["artist"] == "Artist V"
    assert group["title"] == "Album Z"
    assert group["year_span"] == "1990-2020"
    assert group["release_count"] == 3


def test_run_duplicate_variant_detector_handles_empty_list(monkeypatch):
    monkeypatch.setattr(
        duplicate_variant_detector, "run_list_releases", lambda **kwargs: []
    )

    result = duplicate_variant_detector.run_duplicate_variant_detector()

    assert result["active_release_count"] == 0
    assert result["duplicate_group_count"] == 0
    assert result["variant_group_count"] == 0
    assert result["confidence_score"] is None


def test_run_duplicate_variant_detector_validates_args():
    with pytest.raises(ValueError):
        duplicate_variant_detector.run_duplicate_variant_detector(group_limit=0)
