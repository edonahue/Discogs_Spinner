"""Tests for the Price Refresh Prioritizer use case.

Covers:
- run_value_refresh_queue returns expected keys
- priority ordering: missing < unpriced < stale
- within stale tier: highest median first
- limit is respected
- stale_days validation
- limit validation
- empty collection returns zero counts
- source-level: CLI command wired to use case
"""

from __future__ import annotations

from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Source-level assertions (no DB needed)
# ---------------------------------------------------------------------------

_COMMANDS = (
    Path(__file__).parents[1] / "src" / "discogs_player" / "cli" / "commands.py"
)
_USE_CASE = (
    Path(__file__).parents[1]
    / "src"
    / "discogs_player"
    / "use_cases"
    / "value_refresh_queue.py"
)


def test_use_case_file_exists():
    assert _USE_CASE.exists(), "value_refresh_queue.py must exist"


def test_cli_imports_run_value_refresh_queue():
    assert "run_value_refresh_queue" in _COMMANDS.read_text()


def test_cli_has_queue_command():
    src = _COMMANDS.read_text()
    assert 'value_app.command("queue")' in src
    assert "run_value_refresh_queue" in src


def test_use_case_exports_run_function():
    src = _USE_CASE.read_text()
    assert "def run_value_refresh_queue" in src


def test_use_case_documents_priority_order():
    src = _USE_CASE.read_text()
    assert "missing" in src
    assert "unpriced" in src
    assert "stale" in src


# ---------------------------------------------------------------------------
# Logic unit tests (pure — no DB)
# ---------------------------------------------------------------------------

from discogs_player.use_cases.value_refresh_queue import _PRIORITY, _sort_key


def _make_item(reason: str, median: float | None = None, artist: str = "A") -> dict:
    return {
        "market_need_reason": reason,
        "market_median": median,
        "artist": artist,
        "title": "T",
        "discogs_release_id": 1,
    }


def test_priority_map_ordering():
    assert _PRIORITY["missing"] < _PRIORITY["unpriced"]
    assert _PRIORITY["unpriced"] < _PRIORITY["stale"]
    assert _PRIORITY["stale"] < _PRIORITY["unknown"]


def test_sort_key_missing_before_unpriced():
    assert _sort_key(_make_item("missing")) < _sort_key(_make_item("unpriced"))


def test_sort_key_unpriced_before_stale():
    assert _sort_key(_make_item("unpriced")) < _sort_key(_make_item("stale", median=100.0))


def test_sort_key_stale_high_value_before_low_value():
    high = _make_item("stale", median=200.0, artist="B")
    low = _make_item("stale", median=10.0, artist="A")
    assert _sort_key(high) < _sort_key(low)


def test_sort_key_none_median_treated_as_zero():
    with_value = _make_item("stale", median=5.0, artist="B")
    no_value = _make_item("stale", median=None, artist="A")
    assert _sort_key(with_value) < _sort_key(no_value)


def test_sort_key_artist_tiebreak():
    a1 = _make_item("stale", median=10.0, artist="zzz")
    a2 = _make_item("stale", median=10.0, artist="aaa")
    assert _sort_key(a2) < _sort_key(a1)


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------

from discogs_player.use_cases.value_refresh_queue import run_value_refresh_queue


def test_limit_zero_raises():
    with pytest.raises(ValueError, match="limit"):
        run_value_refresh_queue(limit=0, stale_days=30)


def test_stale_days_negative_raises():
    with pytest.raises(ValueError, match="stale_days"):
        run_value_refresh_queue(limit=10, stale_days=-1)


# ---------------------------------------------------------------------------
# Integration tests (isolated_xdg DB fixture)
# ---------------------------------------------------------------------------


def test_run_value_refresh_queue_empty_db(isolated_xdg):
    """Empty DB returns valid structure with zero counts."""
    result = run_value_refresh_queue(limit=25, stale_days=30)
    assert isinstance(result, dict)
    assert result["total_candidates"] == 0
    assert result["missing_count"] == 0
    assert result["unpriced_count"] == 0
    assert result["stale_count"] == 0
    assert result["queue"] == []
    assert result["limit"] == 25
    assert result["stale_days"] == 30


def test_run_value_refresh_queue_returns_required_keys(isolated_xdg):
    result = run_value_refresh_queue(limit=5)
    for key in ("total_candidates", "missing_count", "unpriced_count",
                "stale_count", "stale_days", "limit", "queue"):
        assert key in result, f"Missing key: {key}"


def test_run_value_refresh_queue_limit_respected(isolated_xdg):
    result = run_value_refresh_queue(limit=3, stale_days=30)
    assert len(result["queue"]) <= 3
