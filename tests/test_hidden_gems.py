"""Tests for the Hidden Gems use case (value × scarcity ranking)."""

from __future__ import annotations

import pytest

from discogs_player.data.db import get_connection
from discogs_player.data.repo import upsert_market_price, upsert_releases
from discogs_player.use_cases.hidden_gems import (
    _gem_score,
    _reason_tags,
    _scarcity,
    run_hidden_gems,
)


def _release(
    release_id: int,
    *,
    artist: str,
    title: str,
    year: int | None,
) -> dict[str, object]:
    return {
        "discogs_release_id": release_id,
        "artist": artist,
        "title": title,
        "year": year,
        "genres": [],
        "styles": [],
        "thumb_url": None,
        "cover_url": None,
        "added_at": "2026-01-01T00:00:00Z",
        "last_synced_at": "2026-01-01T00:00:00Z",
        "is_active": 1,
    }


def _insert_stats(
    conn,
    release_id: int,
    *,
    num_for_sale: int | None = None,
    community_have: int | None = None,
    community_want: int | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO release_stats (
            discogs_release_id, num_for_sale, lowest_price,
            community_have, community_want, rating_count, rating_average,
            last_updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            release_id,
            num_for_sale,
            None,
            community_have,
            community_want,
            0,
            0.0,
            "2026-01-01T00:00:00Z",
        ),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Pure scoring unit tests
# ---------------------------------------------------------------------------


def test_scarcity_maxes_at_zero_for_sale():
    assert _scarcity(0) == pytest.approx(1.0)


def test_scarcity_decreases_as_supply_increases():
    assert _scarcity(1) > _scarcity(5) > _scarcity(50)


def test_scarcity_handles_none():
    assert _scarcity(None) == pytest.approx(0.1)


def test_gem_score_rewards_value_and_scarcity():
    low_supply = _gem_score(median=50.0, num_for_sale=0, community_want=0, community_have=1)
    high_supply = _gem_score(median=50.0, num_for_sale=100, community_want=0, community_have=1)
    assert low_supply > high_supply


def test_gem_score_rewards_community_demand():
    cold = _gem_score(median=50.0, num_for_sale=1, community_want=0, community_have=100)
    hot = _gem_score(median=50.0, num_for_sale=1, community_want=200, community_have=100)
    assert hot > cold


def test_reason_tags_scarce_when_zero_for_sale():
    tags = _reason_tags(
        median=30.0, year=1975, num_for_sale=0, community_have=10, community_want=5
    )
    assert "scarce-now" in tags


def test_reason_tags_high_value_threshold():
    assert "high-value" in _reason_tags(
        median=50.0, year=1975, num_for_sale=10, community_have=10, community_want=5
    )
    assert "high-value" not in _reason_tags(
        median=49.0, year=1975, num_for_sale=10, community_have=10, community_want=5
    )


def test_reason_tags_surprising_for_modern_reissue():
    assert "surprising" in _reason_tags(
        median=140.0, year=2017, num_for_sale=3, community_have=10, community_want=5
    )
    assert "surprising" not in _reason_tags(
        median=140.0, year=1975, num_for_sale=3, community_have=10, community_want=5
    )


def test_reason_tags_community_hot_when_want_exceeds_have():
    tags = _reason_tags(
        median=30.0, year=1980, num_for_sale=5, community_have=10, community_want=50
    )
    assert "community-hot" in tags


# ---------------------------------------------------------------------------
# End-to-end with isolated DB
# ---------------------------------------------------------------------------


def test_run_hidden_gems_surfaces_scarce_valuable_releases(isolated_xdg):
    conn = get_connection()
    try:
        upsert_releases(
            conn,
            [
                _release(1, artist="Kaki King", title="Everybody Loves You", year=2010),
                _release(2, artist="Common Release", title="Cheap LP", year=1980),
                _release(3, artist="Bob Schneider", title="A Perfect Day", year=2011),
            ],
        )
        # High value + zero for sale → should top the list
        upsert_market_price(
            conn,
            discogs_release_id=1,
            lowest=70.0,
            median=80.5,
            highest=100.0,
            currency="USD",
            last_updated_at="2026-01-01T00:00:00Z",
        )
        _insert_stats(conn, 1, num_for_sale=0, community_have=101, community_want=120)

        # Low value → filtered out by min_median
        upsert_market_price(
            conn,
            discogs_release_id=2,
            lowest=2.0,
            median=5.0,
            highest=10.0,
            currency="USD",
            last_updated_at="2026-01-01T00:00:00Z",
        )
        _insert_stats(conn, 2, num_for_sale=50, community_have=1000, community_want=50)

        # Also high value + zero for sale
        upsert_market_price(
            conn,
            discogs_release_id=3,
            lowest=70.0,
            median=80.0,
            highest=100.0,
            currency="USD",
            last_updated_at="2026-01-01T00:00:00Z",
        )
        _insert_stats(conn, 3, num_for_sale=0, community_have=102, community_want=60)
    finally:
        conn.close()

    result = run_hidden_gems(min_median=25.0, limit=10)

    assert result["ok"] is True
    assert result["count"] == 2  # cheap LP filtered out
    gems = result["gems"]
    assert isinstance(gems, list)
    ids = [g["discogs_release_id"] for g in gems]
    assert 1 in ids and 3 in ids
    assert 2 not in ids

    top = gems[0]
    assert "scarce-now" in top["reasons"]
    assert "high-value" in top["reasons"]
    assert "surprising" in top["reasons"]  # year >= 2000 + median >= 50
    assert top["gem_score"] > gems[-1]["gem_score"]


def test_run_hidden_gems_respects_limit(isolated_xdg):
    conn = get_connection()
    try:
        upsert_releases(
            conn,
            [
                _release(i, artist=f"Artist {i}", title=f"Title {i}", year=1980)
                for i in range(1, 6)
            ],
        )
        for i in range(1, 6):
            upsert_market_price(
                conn,
                discogs_release_id=i,
                lowest=20.0,
                median=30.0 + i,
                highest=40.0,
                currency="USD",
                last_updated_at="2026-01-01T00:00:00Z",
            )
            _insert_stats(conn, i, num_for_sale=i, community_have=10, community_want=5)
    finally:
        conn.close()

    result = run_hidden_gems(min_median=25.0, limit=3)
    assert result["count"] == 3


def test_run_hidden_gems_validates_inputs():
    with pytest.raises(ValueError):
        run_hidden_gems(min_median=-1.0)
    with pytest.raises(ValueError):
        run_hidden_gems(limit=0)


def test_run_hidden_gems_skips_inactive_releases(isolated_xdg):
    conn = get_connection()
    try:
        upsert_releases(
            conn,
            [_release(1, artist="Rare Artist", title="Rare Album", year=2010)],
        )
        # Mark inactive (simulate removed from collection)
        conn.execute("UPDATE releases SET is_active = 0 WHERE discogs_release_id = 1")
        upsert_market_price(
            conn,
            discogs_release_id=1,
            lowest=50.0,
            median=100.0,
            highest=200.0,
            currency="USD",
            last_updated_at="2026-01-01T00:00:00Z",
        )
        _insert_stats(conn, 1, num_for_sale=0, community_have=10, community_want=5)
    finally:
        conn.close()

    result = run_hidden_gems(min_median=25.0, limit=10)
    assert result["count"] == 0
