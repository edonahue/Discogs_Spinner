from __future__ import annotations

from discogs_player.data.db import get_connection
from discogs_player.data.repo import upsert_market_price, upsert_releases
from discogs_player.use_cases.release_collection_summary import (
    run_release_collection_summary,
)


def _release(
    release_id: int,
    *,
    artist: str,
    title: str,
    year: int,
    genres: list[str],
    styles: list[str],
    added_at: str,
    has_lp: bool | None = None,
    has_45: bool | None = None,
    is_active: int = 1,
) -> dict[str, object]:
    return {
        "discogs_release_id": release_id,
        "artist": artist,
        "title": title,
        "year": year,
        "genres": genres,
        "styles": styles,
        "thumb_url": None,
        "cover_url": None,
        "added_at": added_at,
        "last_synced_at": "2026-04-18T14:00:00Z",
        "has_lp": has_lp,
        "has_45": has_45,
        "is_active": is_active,
    }


def test_release_collection_summary_honors_filters_and_recent_release(isolated_xdg):
    conn = get_connection()
    try:
        upsert_releases(
            conn,
            [
                _release(
                    1,
                    artist="Miles Davis",
                    title="Kind of Blue",
                    year=1959,
                    genres=["Jazz"],
                    styles=["Modal"],
                    added_at="2026-04-18T14:00:00Z",
                    has_lp=True,
                    has_45=False,
                ),
                _release(
                    2,
                    artist="The Beatles",
                    title="Paperback Writer",
                    year=1966,
                    genres=["Rock"],
                    styles=["Pop Rock"],
                    added_at="2026-04-17T09:30:00Z",
                    has_lp=False,
                    has_45=True,
                ),
                _release(
                    3,
                    artist="John Coltrane",
                    title="A Love Supreme",
                    year=1965,
                    genres=["Jazz"],
                    styles=["Modal"],
                    added_at="2026-04-16T08:15:00Z",
                    has_lp=True,
                    has_45=False,
                ),
            ],
        )
        upsert_market_price(
            conn,
            discogs_release_id=1,
            lowest=20.0,
            median=24.99,
            highest=30.0,
            currency="USD",
            last_updated_at="2026-04-18T14:00:00Z",
        )
        upsert_market_price(
            conn,
            discogs_release_id=3,
            lowest=22.0,
            median=26.5,
            highest=33.0,
            currency="USD",
            last_updated_at="2026-04-18T14:00:00Z",
        )
    finally:
        conn.close()

    summary = run_release_collection_summary(
        q="miles",
        genres=["Jazz"],
        styles=["Modal"],
        year="1959:1960",
    )

    assert summary["release_count"] == 1
    assert summary["lp_count"] == 1
    assert summary["rpm45_count"] == 0
    assert summary["format_counts_ready"] is True
    assert summary["priced_release_count"] == 1
    assert summary["total_median"] == 24.99
    assert summary["median_currency"] == "USD"
    assert summary["mixed_currencies"] is False
    assert summary["most_recent_release_id"] == 1
    assert summary["most_recent_release_artist"] == "Miles Davis"
    assert summary["most_recent_release_title"] == "Kind of Blue"


def test_release_collection_summary_marks_formats_unready_when_sync_data_missing(
    isolated_xdg,
):
    conn = get_connection()
    try:
        upsert_releases(
            conn,
            [
                _release(
                    11,
                    artist="Alpha",
                    title="Unknown Format",
                    year=1980,
                    genres=["Rock"],
                    styles=["Indie Rock"],
                    added_at="2026-04-12T10:00:00Z",
                    has_lp=None,
                    has_45=None,
                ),
                _release(
                    12,
                    artist="Beta",
                    title="Known LP",
                    year=1981,
                    genres=["Rock"],
                    styles=["Indie Rock"],
                    added_at="2026-04-13T10:00:00Z",
                    has_lp=True,
                    has_45=False,
                ),
            ],
        )
    finally:
        conn.close()

    summary = run_release_collection_summary(genres=["Rock"])

    assert summary["release_count"] == 2
    assert summary["lp_count"] == 1
    assert summary["rpm45_count"] == 0
    assert summary["format_counts_ready"] is False
    assert summary["total_median"] is None
    assert summary["priced_release_count"] == 0


def test_release_collection_summary_detects_mixed_currencies(isolated_xdg):
    conn = get_connection()
    try:
        upsert_releases(
            conn,
            [
                _release(
                    21,
                    artist="Can",
                    title="Future Days",
                    year=1973,
                    genres=["Rock"],
                    styles=["Krautrock"],
                    added_at="2026-04-10T10:00:00Z",
                    has_lp=True,
                    has_45=False,
                ),
                _release(
                    22,
                    artist="Neu!",
                    title="Neu! 75",
                    year=1975,
                    genres=["Rock"],
                    styles=["Krautrock"],
                    added_at="2026-04-11T10:00:00Z",
                    has_lp=True,
                    has_45=False,
                ),
            ],
        )
        upsert_market_price(
            conn,
            discogs_release_id=21,
            lowest=18.0,
            median=22.0,
            highest=27.0,
            currency="USD",
            last_updated_at="2026-04-18T14:00:00Z",
        )
        upsert_market_price(
            conn,
            discogs_release_id=22,
            lowest=16.0,
            median=19.0,
            highest=25.0,
            currency="EUR",
            last_updated_at="2026-04-18T14:00:00Z",
        )
    finally:
        conn.close()

    summary = run_release_collection_summary(styles=["Krautrock"])

    assert summary["release_count"] == 2
    assert summary["priced_release_count"] == 2
    assert summary["total_median"] == 41.0
    assert summary["median_currency"] is None
    assert summary["mixed_currencies"] is True
