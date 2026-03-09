"""Tests for the Collection Health Score use case.

Covers:
- run_collection_health returns expected keys and structure
- score is in 0-100 range
- buckets contain required fields
- empty collection returns score=100 (no gaps to penalise)
- score decreases proportionally with gap count
- source-level: CLI command wired to use case
"""

from __future__ import annotations

from pathlib import Path


# ---------------------------------------------------------------------------
# Source-level assertions
# ---------------------------------------------------------------------------

_COMMANDS = (
    Path(__file__).parents[1] / "src" / "discogs_player" / "cli" / "commands.py"
)
_USE_CASE = (
    Path(__file__).parents[1]
    / "src"
    / "discogs_player"
    / "use_cases"
    / "collection_health.py"
)


def test_use_case_file_exists():
    assert _USE_CASE.exists(), "collection_health.py must exist"


def test_cli_imports_run_collection_health():
    assert "run_collection_health" in _COMMANDS.read_text()


def test_cli_has_health_command():
    src = _COMMANDS.read_text()
    assert 'app.command("health")' in src
    assert "run_collection_health" in src


def test_use_case_exports_run_function():
    assert "def run_collection_health" in _USE_CASE.read_text()


def test_use_case_defines_five_buckets():
    src = _USE_CASE.read_text()
    for bucket in ("missing_price", "missing_year", "missing_genres",
                   "missing_cover", "unmatched_spotify"):
        assert bucket in src, f"Bucket '{bucket}' not found in collection_health.py"


# ---------------------------------------------------------------------------
# Score formula unit tests (pure)
# ---------------------------------------------------------------------------

from discogs_player.use_cases.collection_health import _pct, _deduction


def test_pct_zero_denominator():
    assert _pct(5, 0) == 0.0


def test_pct_all_gap():
    assert _pct(10, 10) == 100.0


def test_pct_half_gap():
    assert _pct(5, 10) == 50.0


def test_deduction_zero_total():
    assert _deduction(5, 0, 20.0) == 0.0


def test_deduction_capped_at_max():
    assert _deduction(100, 100, 20.0) == 20.0


def test_deduction_proportional():
    result = _deduction(5, 10, 20.0)
    assert result == 10.0


def test_deduction_never_exceeds_max():
    result = _deduction(1000, 1000, 20.0)
    assert result <= 20.0


# ---------------------------------------------------------------------------
# Integration tests (isolated_xdg DB fixture)
# ---------------------------------------------------------------------------

from discogs_player.use_cases.collection_health import run_collection_health


def test_run_collection_health_empty_db(isolated_xdg):
    """Empty collection: no releases, score should be 100 (no gaps)."""
    result = run_collection_health()
    assert isinstance(result, dict)
    assert "score" in result
    assert "total_active" in result
    assert "buckets" in result
    assert result["total_active"] == 0
    assert result["score"] == 100


def test_run_collection_health_score_in_range(isolated_xdg):
    result = run_collection_health()
    score = result["score"]
    assert isinstance(score, int)
    assert 0 <= score <= 100


def test_run_collection_health_buckets_structure(isolated_xdg):
    result = run_collection_health()
    buckets = result["buckets"]
    assert isinstance(buckets, list)
    assert len(buckets) == 5
    for b in buckets:
        assert "name" in b
        assert "label" in b
        assert "gap_count" in b
        assert "gap_pct" in b
        assert "max_deduction" in b
        assert "deduction" in b


def test_run_collection_health_bucket_names(isolated_xdg):
    result = run_collection_health()
    names = {b["name"] for b in result["buckets"]}
    assert names == {
        "missing_price", "missing_year", "missing_genres",
        "missing_cover", "unmatched_spotify",
    }


def test_run_collection_health_deductions_non_negative(isolated_xdg):
    result = run_collection_health()
    for b in result["buckets"]:
        assert float(b["deduction"]) >= 0.0


def test_run_collection_health_total_deduction_matches_score(isolated_xdg):
    result = run_collection_health()
    total_ded = sum(
        float(b["deduction"]) if isinstance(b["deduction"], (int, float)) else 0.0
        for b in result["buckets"]
    )
    expected_score = max(0, round(100.0 - total_ded))
    assert result["score"] == expected_score
