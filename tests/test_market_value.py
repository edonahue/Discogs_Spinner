from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone

import pytest

from discogs_player.core.settings import set_setting
from discogs_player.data.db import get_connection
from discogs_player.data.repo import (
    get_market_price,
    insert_market_value_snapshot,
    query_market_value_snapshots,
    upsert_market_price,
    upsert_releases,
)
from discogs_player.services.discogs_client import DiscogsApiError
from discogs_player.services.sync_manager import MissingDiscogsTokenError
from discogs_player.use_cases import value_refresh
from discogs_player.use_cases import value_show as value_show_use_case
from discogs_player.use_cases.value_missing import run_market_value_missing
from discogs_player.use_cases.value_missing import write_market_value_missing_csv
from discogs_player.use_cases.duplicate_variant_detector import (
    run_duplicate_variant_detector,
)
from discogs_player.use_cases.value_examples import run_market_value_examples
from discogs_player.use_cases.value_dashboard import run_market_value_dashboard
from discogs_player.use_cases.value_refresh import run_refresh_market_values
from discogs_player.use_cases.value_snapshot import run_market_value_snapshot
from discogs_player.use_cases.value_show import run_market_value_show
from discogs_player.use_cases.value_status import run_market_value_status
from discogs_player.use_cases.value_trend import run_market_value_trend


def _release(release_id: int, *, is_active: int = 1) -> dict[str, object]:
    return {
        "discogs_release_id": release_id,
        "artist": f"Artist {release_id}",
        "title": f"Album {release_id}",
        "year": 2000,
        "genres": ["Rock"],
        "styles": ["Alt"],
        "thumb_url": None,
        "cover_url": None,
        "added_at": "2026-01-01T00:00:00Z",
        "last_synced_at": "2026-01-01T00:00:00Z",
        "is_active": is_active,
    }


def test_market_value_status_aggregates_active_collection(isolated_xdg):
    conn = get_connection()
    try:
        upsert_releases(conn, [_release(1), _release(2), _release(3, is_active=0)])
        upsert_market_price(
            conn,
            discogs_release_id=1,
            lowest=10.0,
            median=15.0,
            highest=20.0,
            currency="USD",
            last_updated_at="2026-02-05T00:00:00+00:00",
        )
        upsert_market_price(
            conn,
            discogs_release_id=2,
            lowest=5.0,
            median=8.0,
            highest=12.0,
            currency="EUR",
            last_updated_at="2026-02-06T00:00:00+00:00",
        )
        upsert_market_price(
            conn,
            discogs_release_id=3,
            lowest=99.0,
            median=101.0,
            highest=120.0,
            currency="USD",
            last_updated_at="2026-02-07T00:00:00+00:00",
        )
    finally:
        conn.close()

    summary = run_market_value_status()

    assert summary["active_release_count"] == 2
    assert summary["priced_release_count"] == 2
    assert summary["unpriced_release_count"] == 0
    assert summary["total_lowest"] == 15.0
    assert summary["total_median"] == 23.0
    assert summary["total_highest"] == 32.0
    assert summary["market_value_last_updated"] == "2026-02-06T00:00:00+00:00"
    assert summary["currency_counts"] == [
        {"currency": "EUR", "count": 1},
        {"currency": "USD", "count": 1},
    ]


def test_market_value_examples_returns_high_and_low_artist_album_rows(isolated_xdg):
    conn = get_connection()
    try:
        upsert_releases(
            conn, [_release(10), _release(20), _release(30), _release(40, is_active=0)]
        )
        upsert_market_price(
            conn,
            discogs_release_id=10,
            lowest=95.0,
            median=100.0,
            highest=110.0,
            currency="USD",
            last_updated_at="2026-02-05T00:00:00+00:00",
        )
        upsert_market_price(
            conn,
            discogs_release_id=20,
            lowest=195.0,
            median=200.0,
            highest=210.0,
            currency="USD",
            last_updated_at="2026-02-06T00:00:00+00:00",
        )
        upsert_market_price(
            conn,
            discogs_release_id=30,
            lowest=4.0,
            median=5.0,
            highest=8.0,
            currency="USD",
            last_updated_at="2026-02-06T00:00:00+00:00",
        )
        upsert_market_price(
            conn,
            discogs_release_id=40,
            lowest=999.0,
            median=1000.0,
            highest=1200.0,
            currency="USD",
            last_updated_at="2026-02-07T00:00:00+00:00",
        )
    finally:
        conn.close()

    report = run_market_value_examples(limit=2)

    assert report["limit"] == 2
    high_ids = [item["discogs_release_id"] for item in report["high_priced"]]
    low_ids = [item["discogs_release_id"] for item in report["low_priced"]]
    assert high_ids == [20, 10]
    assert low_ids == [30, 10]
    assert report["high_priced"][0]["artist"] == "Artist 20"
    assert report["high_priced"][0]["title"] == "Album 20"
    assert report["high_priced"][0]["release_display"] == "Artist 20 - Album 20"


def test_market_value_examples_validates_limit():
    with pytest.raises(ValueError, match="limit must be >= 1"):
        run_market_value_examples(limit=0)


def test_market_value_snapshot_captures_current_totals(isolated_xdg):
    conn = get_connection()
    try:
        upsert_releases(conn, [_release(91), _release(92)])
        upsert_market_price(
            conn,
            discogs_release_id=91,
            lowest=10.0,
            median=12.0,
            highest=15.0,
            currency="USD",
            last_updated_at="2026-02-07T00:00:00+00:00",
        )
    finally:
        conn.close()

    snapshot = run_market_value_snapshot()
    assert snapshot["snapshot_id"] >= 1
    assert snapshot["active_release_count"] == 2
    assert snapshot["priced_release_count"] == 1
    assert snapshot["unpriced_release_count"] == 1
    assert snapshot["total_lowest"] == 10.0
    assert snapshot["total_median"] == 12.0
    assert snapshot["total_highest"] == 15.0

    conn = get_connection()
    try:
        rows = query_market_value_snapshots(conn, limit=1)
    finally:
        conn.close()
    assert len(rows) == 1
    assert rows[0]["id"] == snapshot["snapshot_id"]
    assert rows[0]["total_median"] == 12.0


def test_market_value_trend_reports_deltas(isolated_xdg):
    conn = get_connection()
    try:
        insert_market_value_snapshot(
            conn,
            captured_at="2026-02-06T00:00:00+00:00",
            active_release_count=10,
            priced_release_count=8,
            unpriced_release_count=2,
            total_lowest=100.0,
            total_median=120.0,
            total_highest=150.0,
        )
        insert_market_value_snapshot(
            conn,
            captured_at="2026-02-07T00:00:00+00:00",
            active_release_count=10,
            priced_release_count=9,
            unpriced_release_count=1,
            total_lowest=102.0,
            total_median=126.0,
            total_highest=158.0,
        )
        insert_market_value_snapshot(
            conn,
            captured_at="2026-02-08T00:00:00+00:00",
            active_release_count=11,
            priced_release_count=10,
            unpriced_release_count=1,
            total_lowest=108.0,
            total_median=135.0,
            total_highest=168.0,
        )
    finally:
        conn.close()

    report = run_market_value_trend(limit=10)
    assert report["snapshot_count"] == 3
    assert report["window_start"] == "2026-02-06T00:00:00+00:00"
    assert report["window_end"] == "2026-02-08T00:00:00+00:00"
    assert report["window_delta_total_median"] == 15.0
    assert report["window_delta_total_median_percent"] == 12.5

    points = report["points"]
    assert [item["captured_at"] for item in points] == [
        "2026-02-06T00:00:00+00:00",
        "2026-02-07T00:00:00+00:00",
        "2026-02-08T00:00:00+00:00",
    ]
    assert points[0]["delta_total_median"] is None
    assert points[1]["delta_total_median"] == 6.0
    assert points[2]["delta_total_median"] == 9.0


def test_market_value_trend_validates_limit():
    with pytest.raises(ValueError, match="limit must be >= 1"):
        run_market_value_trend(limit=0)


def test_market_value_dashboard_reports_summary_rankings_and_graph_metrics(
    isolated_xdg,
):
    conn = get_connection()
    try:
        upsert_releases(conn, [_release(item_id) for item_id in range(1, 13)])
        for item_id in range(1, 13):
            upsert_market_price(
                conn,
                discogs_release_id=item_id,
                lowest=float(item_id * 7),
                median=float(item_id * 10),
                highest=float(item_id * 12),
                currency="USD" if item_id % 2 else "EUR",
                last_updated_at="2026-02-08T00:00:00+00:00",
            )

        insert_market_value_snapshot(
            conn,
            captured_at="2026-02-07T00:00:00+00:00",
            active_release_count=12,
            priced_release_count=12,
            unpriced_release_count=0,
            total_lowest=500.0,
            total_median=600.0,
            total_highest=700.0,
        )
        insert_market_value_snapshot(
            conn,
            captured_at="2026-02-08T00:00:00+00:00",
            active_release_count=12,
            priced_release_count=12,
            unpriced_release_count=0,
            total_lowest=550.0,
            total_median=720.0,
            total_highest=860.0,
        )
    finally:
        conn.close()

    report = run_market_value_dashboard(top_limit=10, bottom_limit=2, trend_limit=8)

    assert report["top_limit"] == 10
    assert report["bottom_limit"] == 2
    assert report["trend_limit"] == 8

    summary = report["summary"]
    assert summary["active_release_count"] == 12
    assert summary["priced_release_count"] == 12
    assert summary["unpriced_release_count"] == 0

    coverage = report["coverage"]
    assert coverage["active_release_count"] == 12
    assert coverage["priced_release_count"] == 12
    assert coverage["unpriced_release_count"] == 0
    assert coverage["ratio"] == 1.0

    top_ids = [row["discogs_release_id"] for row in report["top_priced"]]
    bottom_ids = [row["discogs_release_id"] for row in report["bottom_priced"]]
    assert top_ids == [12, 11, 10, 9, 8, 7, 6, 5, 4, 3]
    assert bottom_ids == [1, 2]

    value_bands = report["value_bands"]
    assert [item["key"] for item in value_bands] == ["low", "median", "high"]
    assert value_bands[2]["ratio"] == 1.0
    assert value_bands[1]["ratio"] < value_bands[2]["ratio"]

    currency_mix = report["currency_mix"]
    assert currency_mix == [
        {"currency": "EUR", "count": 6, "ratio": 0.5},
        {"currency": "USD", "count": 6, "ratio": 0.5},
    ]

    trend = report["trend"]
    assert trend["snapshot_count"] == 2
    assert trend["window_start"] == "2026-02-07T00:00:00+00:00"
    assert trend["window_end"] == "2026-02-08T00:00:00+00:00"
    assert trend["window_delta_total_median"] == 120.0
    assert trend["window_delta_total_median_percent"] == 20.0
    assert [point["label"] for point in trend["points"]] == ["2026-02-07", "2026-02-08"]
    assert trend["points"][-1]["ratio"] == 1.0

    detector = report["detector"]
    assert detector["group_limit"] == 8
    assert detector["active_release_count"] == 12
    assert detector["confidence_score"] is None
    assert detector["confidence_percent"] is None


def test_market_value_dashboard_validates_limits():
    with pytest.raises(ValueError, match="top_limit must be >= 1"):
        run_market_value_dashboard(top_limit=0)
    with pytest.raises(ValueError, match="bottom_limit must be >= 1"):
        run_market_value_dashboard(bottom_limit=0)
    with pytest.raises(ValueError, match="trend_limit must be >= 1"):
        run_market_value_dashboard(trend_limit=0)
    with pytest.raises(ValueError, match="detector_limit must be >= 1"):
        run_market_value_dashboard(detector_limit=0)


def test_duplicate_variant_detector_finds_duplicate_groups_and_variant_families(
    isolated_xdg,
):
    a1 = _release(301)
    a1["artist"] = "Band A"
    a1["title"] = "Shared Album"
    a1["year"] = 1990
    a1["styles"] = ["House"]

    a2 = _release(302)
    a2["artist"] = "Band A"
    a2["title"] = "Shared Album"
    a2["year"] = 1990
    a2["styles"] = ["House"]

    a3 = _release(303)
    a3["artist"] = "Band A"
    a3["title"] = "Shared Album"
    a3["year"] = 1992
    a3["styles"] = ["House"]

    b1 = _release(304)
    b1["artist"] = "Band B"
    b1["title"] = "Another Album"
    b1["year"] = 2001
    b1["styles"] = ["Techno"]

    b2 = _release(305)
    b2["artist"] = "Band B"
    b2["title"] = "Another Album"
    b2["year"] = 2001
    b2["styles"] = ["Techno"]

    c1 = _release(306)
    c1["artist"] = "Band C"
    c1["title"] = "Unique Album"
    c1["year"] = 2004

    conn = get_connection()
    try:
        upsert_releases(conn, [a1, a2, a3, b1, b2, c1])
        upsert_market_price(
            conn,
            discogs_release_id=301,
            lowest=10.0,
            median=15.0,
            highest=20.0,
            currency="USD",
            last_updated_at="2026-02-08T00:00:00+00:00",
        )
        upsert_market_price(
            conn,
            discogs_release_id=302,
            lowest=8.0,
            median=11.0,
            highest=15.0,
            currency="USD",
            last_updated_at="2026-02-08T00:00:00+00:00",
        )
        upsert_market_price(
            conn,
            discogs_release_id=303,
            lowest=20.0,
            median=25.0,
            highest=30.0,
            currency="USD",
            last_updated_at="2026-02-08T00:00:00+00:00",
        )
        upsert_market_price(
            conn,
            discogs_release_id=304,
            lowest=40.0,
            median=45.0,
            highest=50.0,
            currency="USD",
            last_updated_at="2026-02-08T00:00:00+00:00",
        )
        upsert_market_price(
            conn,
            discogs_release_id=305,
            lowest=42.0,
            median=47.0,
            highest=52.0,
            currency="USD",
            last_updated_at="2026-02-08T00:00:00+00:00",
        )
    finally:
        conn.close()

    report = run_duplicate_variant_detector(group_limit=10)

    assert report["group_limit"] == 10
    assert report["active_release_count"] == 6
    assert report["duplicate_group_count"] == 2
    assert report["duplicate_release_count"] == 4
    assert isinstance(report["duplicate_confidence_score"], float)
    assert 0.0 <= report["duplicate_confidence_score"] <= 1.0
    assert isinstance(report["duplicate_confidence_percent"], int)
    assert report["variant_group_count"] == 1
    assert report["variant_release_count"] == 3
    assert isinstance(report["variant_confidence_score"], float)
    assert 0.0 <= report["variant_confidence_score"] <= 1.0
    assert isinstance(report["variant_confidence_percent"], int)
    assert isinstance(report["confidence_score"], float)
    assert 0.0 <= report["confidence_score"] <= 1.0
    assert isinstance(report["confidence_percent"], int)

    duplicate_group_labels = [
        group["group_label"] for group in report["duplicate_groups"]
    ]
    assert "Band A - Shared Album (1990)" in duplicate_group_labels
    assert "Band B - Another Album (2001)" in duplicate_group_labels
    for group in report["duplicate_groups"]:
        assert isinstance(group["confidence_score"], float)
        assert 0.0 <= group["confidence_score"] <= 1.0
        assert isinstance(group["confidence_percent"], int)
        assert 0 <= group["confidence_percent"] <= 100

    variant_group = report["variant_groups"][0]
    assert variant_group["group_label"] == "Band A - Shared Album (1990-1992)"
    assert variant_group["release_count"] == 3
    assert isinstance(variant_group["confidence_score"], float)
    assert 0.0 <= variant_group["confidence_score"] <= 1.0
    assert isinstance(variant_group["confidence_percent"], int)
    assert 0 <= variant_group["confidence_percent"] <= 100
    variant_ids = [item["discogs_release_id"] for item in variant_group["items"]]
    assert variant_ids == [303, 301, 302]


def test_duplicate_variant_detector_validates_group_limit():
    with pytest.raises(ValueError, match="group_limit must be >= 1"):
        run_duplicate_variant_detector(group_limit=0)


def test_market_value_show_returns_release_and_cached_price(isolated_xdg):
    conn = get_connection()
    try:
        upsert_releases(conn, [_release(55)])
        upsert_market_price(
            conn,
            discogs_release_id=55,
            lowest=9.0,
            median=11.0,
            highest=14.0,
            currency="USD",
            last_updated_at="2026-02-07T00:00:00+00:00",
        )
    finally:
        conn.close()

    item = run_market_value_show(55)
    assert item["discogs_release_id"] == 55
    assert item["artist"] == "Artist 55"
    assert item["market_lowest"] == 9.0
    assert item["market_median"] == 11.0
    assert item["market_highest"] == 14.0
    assert item["market_currency"] == "USD"
    assert item["market_last_updated_at"] == "2026-02-07T00:00:00+00:00"
    assert item["market_spread"] == 5.0
    assert item["market_midpoint"] == 11.5
    assert item["market_price_point_count"] == 3
    assert item["has_market_value"] is True


def test_market_value_show_requires_existing_release(isolated_xdg):
    with pytest.raises(ValueError, match="Release not found"):
        run_market_value_show(999999)


def test_market_value_show_refresh_updates_cached_price(isolated_xdg, monkeypatch):
    conn = get_connection()
    try:
        upsert_releases(conn, [_release(56)])
        upsert_market_price(
            conn,
            discogs_release_id=56,
            lowest=1.0,
            median=2.0,
            highest=3.0,
            currency="USD",
            last_updated_at="2026-01-01T00:00:00+00:00",
        )
    finally:
        conn.close()

    monkeypatch.setenv("DISCOGS_TOKEN", "token")

    class _FakeClient:
        def __init__(self, token: str):
            self.token = token

        def fetch_market_price_suggestions(self, discogs_release_id: int):
            assert discogs_release_id == 56
            return {"lowest": 10.0, "median": 12.0, "highest": 16.0, "currency": "USD"}

    monkeypatch.setattr(value_show_use_case, "DiscogsClient", _FakeClient)
    item = run_market_value_show(56, refresh=True)

    assert item["market_lowest"] == 10.0
    assert item["market_median"] == 12.0
    assert item["market_highest"] == 16.0
    assert item["market_currency"] == "USD"
    assert item["market_last_updated_at"] is not None

    conn = get_connection()
    try:
        price = get_market_price(conn, 56)
    finally:
        conn.close()

    assert price is not None
    assert price["median"] == 12.0
    assert price["last_updated_at"] is not None


def test_market_value_show_refresh_requires_discogs_token(isolated_xdg, monkeypatch):
    conn = get_connection()
    try:
        upsert_releases(conn, [_release(57)])
    finally:
        conn.close()

    monkeypatch.delenv("DISCOGS_TOKEN", raising=False)
    with pytest.raises(MissingDiscogsTokenError):
        run_market_value_show(57, refresh=True)


def test_market_value_missing_lists_active_unpriced_releases(isolated_xdg):
    conn = get_connection()
    try:
        upsert_releases(
            conn, [_release(61), _release(62), _release(63), _release(64, is_active=0)]
        )
        upsert_market_price(
            conn,
            discogs_release_id=62,
            lowest=1.0,
            median=2.0,
            highest=3.0,
            currency="USD",
            last_updated_at="2026-02-07T00:00:00+00:00",
        )
        upsert_market_price(
            conn,
            discogs_release_id=63,
            lowest=None,
            median=None,
            highest=None,
            currency="USD",
            last_updated_at="2026-02-07T00:00:00+00:00",
        )
    finally:
        conn.close()

    items = run_market_value_missing(limit=10)
    assert [item["discogs_release_id"] for item in items] == [61, 63]
    assert [item["market_need_reason"] for item in items] == ["missing", "unpriced"]


def test_market_value_missing_validates_limit():
    with pytest.raises(ValueError, match="limit must be >= 1"):
        run_market_value_missing(limit=0)


def test_market_value_missing_validates_stale_days():
    with pytest.raises(ValueError, match="stale_days must be >= 0"):
        run_market_value_missing(limit=5, stale_days=-1)


def test_market_value_missing_can_include_stale_entries(isolated_xdg):
    now = datetime.now(timezone.utc)
    stale_iso = (now - timedelta(days=40)).isoformat()
    fresh_iso = (now - timedelta(days=2)).isoformat()

    conn = get_connection()
    try:
        upsert_releases(conn, [_release(71), _release(72), _release(73)])
        upsert_market_price(
            conn,
            discogs_release_id=71,
            lowest=1.0,
            median=2.0,
            highest=3.0,
            currency="USD",
            last_updated_at=stale_iso,
        )
        upsert_market_price(
            conn,
            discogs_release_id=72,
            lowest=4.0,
            median=5.0,
            highest=6.0,
            currency="USD",
            last_updated_at=fresh_iso,
        )
    finally:
        conn.close()

    items = run_market_value_missing(limit=10, stale_days=30, with_value=True)
    by_id = {int(item["discogs_release_id"]): item for item in items}

    assert set(by_id) == {71, 73}
    assert by_id[71]["market_need_reason"] == "stale"
    assert by_id[71]["market_median"] == 2.0
    assert by_id[73]["market_need_reason"] == "missing"


def test_market_value_missing_csv_export_writes_reason_and_market_fields(
    isolated_xdg, tmp_path
):
    conn = get_connection()
    try:
        upsert_releases(conn, [_release(81), _release(82)])
        upsert_market_price(
            conn,
            discogs_release_id=82,
            lowest=None,
            median=None,
            highest=None,
            currency="USD",
            last_updated_at="2026-02-07T00:00:00+00:00",
        )
    finally:
        conn.close()

    rows = run_market_value_missing(limit=10, with_value=True)
    output = tmp_path / "missing.csv"
    result = write_market_value_missing_csv(releases=rows, output_path=str(output))

    assert result["ok"] is True
    assert result["row_count"] == 2
    assert output.exists()

    with output.open("r", encoding="utf-8", newline="") as handle:
        csv_rows = list(csv.DictReader(handle))

    assert len(csv_rows) == 2
    by_id = {int(item["discogs_release_id"]): item for item in csv_rows}
    assert by_id[81]["market_need_reason"] == "missing"
    assert by_id[82]["market_need_reason"] == "unpriced"
    assert by_id[82]["market_currency"] == "USD"


def test_refresh_market_values_updates_missing_and_stale_entries(
    isolated_xdg, monkeypatch
):
    now = datetime.now(timezone.utc)
    stale_iso = (now - timedelta(days=40)).isoformat()
    fresh_iso = (now - timedelta(days=2)).isoformat()

    conn = get_connection()
    try:
        upsert_releases(conn, [_release(10), _release(20), _release(30)])
        upsert_market_price(
            conn,
            discogs_release_id=20,
            lowest=1.0,
            median=2.0,
            highest=3.0,
            currency="USD",
            last_updated_at=fresh_iso,
        )
        upsert_market_price(
            conn,
            discogs_release_id=30,
            lowest=4.0,
            median=5.0,
            highest=6.0,
            currency="USD",
            last_updated_at=stale_iso,
        )
    finally:
        conn.close()

    monkeypatch.setenv("DISCOGS_TOKEN", "token")

    class _FakeClient:
        def __init__(self, token: str):
            self.token = token

        def fetch_market_price_suggestions(self, discogs_release_id: int):
            if discogs_release_id == 10:
                return {
                    "lowest": 10.0,
                    "median": 11.0,
                    "highest": 14.0,
                    "currency": "USD",
                }
            if discogs_release_id == 30:
                return {
                    "lowest": 30.0,
                    "median": 35.0,
                    "highest": 40.0,
                    "currency": "USD",
                }
            raise AssertionError(f"Unexpected release id {discogs_release_id}")

    monkeypatch.setattr(value_refresh, "DiscogsClient", _FakeClient)
    summary = run_refresh_market_values(limit=10, stale_days=30)

    assert summary["candidate_count"] == 2
    assert summary["refreshed_count"] == 2
    assert summary["priced_count"] == 2
    assert summary["unpriced_count"] == 0
    assert summary["error_count"] == 0
    assert sorted(summary["updated_release_ids"]) == [10, 30]
    assert summary["failed_release_ids"] == []

    conn = get_connection()
    try:
        price_10 = get_market_price(conn, 10)
        price_20 = get_market_price(conn, 20)
        price_30 = get_market_price(conn, 30)
    finally:
        conn.close()

    assert price_10 is not None and price_10["lowest"] == 10.0
    assert price_20 is not None and price_20["lowest"] == 1.0  # unchanged, still fresh
    assert price_30 is not None and price_30["median"] == 35.0


def test_refresh_market_values_continues_on_per_release_api_errors(
    isolated_xdg, monkeypatch
):
    conn = get_connection()
    try:
        upsert_releases(conn, [_release(1), _release(2)])
    finally:
        conn.close()

    monkeypatch.setenv("DISCOGS_TOKEN", "token")

    class _FakeClient:
        def __init__(self, token: str):
            self.token = token

        def fetch_market_price_suggestions(self, discogs_release_id: int):
            if discogs_release_id == 1:
                return {"lowest": 1.0, "median": 2.0, "highest": 3.0, "currency": "USD"}
            raise DiscogsApiError("rate limited")

    monkeypatch.setattr(value_refresh, "DiscogsClient", _FakeClient)
    summary = run_refresh_market_values(limit=10, stale_days=365)

    assert summary["candidate_count"] == 2
    assert summary["refreshed_count"] == 1
    assert summary["error_count"] == 1
    assert summary["updated_release_ids"] == [1]
    assert summary["failed_release_ids"] == [2]
    assert summary["warnings"]

    conn = get_connection()
    try:
        assert get_market_price(conn, 1) is not None
        assert get_market_price(conn, 2) is None
    finally:
        conn.close()


def test_refresh_market_values_release_ids_targets_specific_active_releases(
    isolated_xdg,
    monkeypatch,
):
    conn = get_connection()
    try:
        upsert_releases(
            conn, [_release(101), _release(102), _release(103, is_active=0)]
        )
    finally:
        conn.close()

    monkeypatch.setenv("DISCOGS_TOKEN", "token")

    class _FakeClient:
        def __init__(self, token: str):
            self.token = token

        def fetch_market_price_suggestions(self, discogs_release_id: int):
            return {
                "lowest": float(discogs_release_id),
                "median": float(discogs_release_id) + 1.0,
                "highest": float(discogs_release_id) + 2.0,
                "currency": "USD",
            }

    monkeypatch.setattr(value_refresh, "DiscogsClient", _FakeClient)
    summary = run_refresh_market_values(
        limit=1, stale_days=365, release_ids=[102, 999, 103, 101]
    )

    assert summary["release_ids_requested"] == [102, 999, 103, 101]
    assert summary["candidate_count"] == 2
    assert sorted(summary["updated_release_ids"]) == [101, 102]
    assert summary["skipped_release_ids"] == [999, 103]

    conn = get_connection()
    try:
        assert get_market_price(conn, 101) is not None
        assert get_market_price(conn, 102) is not None
        assert get_market_price(conn, 103) is None
    finally:
        conn.close()


def test_refresh_market_values_from_missing_uses_backlog_selection(
    isolated_xdg,
    monkeypatch,
):
    now = datetime.now(timezone.utc)
    stale_iso = (now - timedelta(days=40)).isoformat()
    fresh_iso = (now - timedelta(days=2)).isoformat()

    conn = get_connection()
    try:
        upsert_releases(
            conn, [_release(201), _release(202), _release(203), _release(204)]
        )
        upsert_market_price(
            conn,
            discogs_release_id=202,
            lowest=None,
            median=None,
            highest=None,
            currency="USD",
            last_updated_at=fresh_iso,
        )
        upsert_market_price(
            conn,
            discogs_release_id=203,
            lowest=1.0,
            median=2.0,
            highest=3.0,
            currency="USD",
            last_updated_at=stale_iso,
        )
        upsert_market_price(
            conn,
            discogs_release_id=204,
            lowest=4.0,
            median=5.0,
            highest=6.0,
            currency="USD",
            last_updated_at=fresh_iso,
        )
    finally:
        conn.close()

    monkeypatch.setenv("DISCOGS_TOKEN", "token")

    class _FakeClient:
        def __init__(self, token: str):
            self.token = token

        def fetch_market_price_suggestions(self, discogs_release_id: int):
            return {
                "lowest": float(discogs_release_id),
                "median": float(discogs_release_id) + 1.0,
                "highest": float(discogs_release_id) + 2.0,
                "currency": "USD",
            }

    monkeypatch.setattr(value_refresh, "DiscogsClient", _FakeClient)
    summary = run_refresh_market_values(limit=10, stale_days=30, from_missing=True)

    assert summary["from_missing"] is True
    assert summary["candidate_count"] == 3
    assert sorted(summary["updated_release_ids"]) == [201, 202, 203]

    conn = get_connection()
    try:
        assert get_market_price(conn, 201) is not None
        assert (
            get_market_price(conn, 202) is not None
            and get_market_price(conn, 202)["median"] == 203.0
        )
        assert (
            get_market_price(conn, 203) is not None
            and get_market_price(conn, 203)["median"] == 204.0
        )
        assert (
            get_market_price(conn, 204) is not None
            and get_market_price(conn, 204)["median"] == 5.0
        )
    finally:
        conn.close()


def test_refresh_market_values_rejects_from_missing_with_release_ids():
    with pytest.raises(ValueError, match="Cannot combine from_missing"):
        run_refresh_market_values(
            limit=10, stale_days=30, release_ids=[1], from_missing=True
        )


def test_refresh_market_values_requires_discogs_token(isolated_xdg, monkeypatch):
    monkeypatch.delenv("DISCOGS_TOKEN", raising=False)
    with pytest.raises(MissingDiscogsTokenError):
        run_refresh_market_values(limit=10, stale_days=30)


def test_refresh_market_values_uses_uppercase_discogs_token_setting(
    isolated_xdg, monkeypatch
):
    monkeypatch.delenv("DISCOGS_TOKEN", raising=False)
    conn = get_connection()
    try:
        upsert_releases(conn, [_release(905)])
        set_setting("DISCOGS_TOKEN", "token-from-settings", conn=conn)
    finally:
        conn.close()

    seen: dict[str, str] = {}

    class _FakeClient:
        def __init__(self, token: str):
            seen["token"] = token

        def fetch_market_price_suggestions(self, discogs_release_id: int):
            return {
                "lowest": float(discogs_release_id),
                "median": float(discogs_release_id) + 1.0,
                "highest": float(discogs_release_id) + 2.0,
                "currency": "USD",
            }

    monkeypatch.setattr(value_refresh, "DiscogsClient", _FakeClient)
    summary = run_refresh_market_values(limit=10, stale_days=30)

    assert seen["token"] == "token-from-settings"
    assert summary["candidate_count"] == 1
    assert summary["refreshed_count"] == 1
