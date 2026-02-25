from __future__ import annotations

import pytest

from discogs_player.core.settings import get_setting
from discogs_player.data.db import get_connection
from discogs_player.data.repo import upsert_market_price, upsert_releases
from discogs_player.use_cases.spin_release import NoReleasesFoundError, run_spin_release


def _release(
    release_id: int,
    *,
    artist: str,
    title: str,
    year: int,
    genres: list[str],
    styles: list[str],
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
        "added_at": "2026-01-01T00:00:00Z",
        "last_synced_at": "2026-01-01T00:00:00Z",
        "is_active": 1,
    }


def test_spin_deterministic_and_persists_last_spin(isolated_xdg):
    conn = get_connection()
    try:
        upsert_releases(
            conn,
            [
                _release(
                    11,
                    artist="A Perfect Circle",
                    title="Thirteenth Step",
                    year=2003,
                    genres=["Rock"],
                    styles=["Alternative"],
                ),
                _release(
                    22,
                    artist="Massive Attack",
                    title="Mezzanine",
                    year=1998,
                    genres=["Electronic"],
                    styles=["Trip Hop"],
                ),
                _release(
                    33,
                    artist="Nina Simone",
                    title="Little Girl Blue",
                    year=1958,
                    genres=["Jazz"],
                    styles=["Soul-Jazz"],
                ),
            ],
        )
        upsert_market_price(
            conn,
            discogs_release_id=11,
            lowest=20.0,
            median=25.0,
            highest=30.0,
            currency="USD",
            last_updated_at="2026-02-08T00:00:00+00:00",
        )
        upsert_market_price(
            conn,
            discogs_release_id=22,
            lowest=10.0,
            median=12.0,
            highest=16.0,
            currency="USD",
            last_updated_at="2026-02-08T00:00:00+00:00",
        )
        upsert_market_price(
            conn,
            discogs_release_id=33,
            lowest=30.0,
            median=35.0,
            highest=42.0,
            currency="USD",
            last_updated_at="2026-02-08T00:00:00+00:00",
        )
    finally:
        conn.close()

    first = run_spin_release(seed=42)
    second = run_spin_release(seed=42)

    assert first["discogs_release_id"] == second["discogs_release_id"]
    assert isinstance(first.get("market_median"), (int, float))
    assert first.get("market_currency") == "USD"

    conn = get_connection()
    try:
        saved = get_setting("last_spin_release_id", conn=conn)
    finally:
        conn.close()

    assert saved == str(second["discogs_release_id"])


def test_spin_respects_filters_and_unmatched(isolated_xdg):
    conn = get_connection()
    try:
        upsert_releases(
            conn,
            [
                _release(
                    101,
                    artist="Artist A",
                    title="A",
                    year=1990,
                    genres=["Rock"],
                    styles=["Indie"],
                ),
                _release(
                    102,
                    artist="Artist B",
                    title="B",
                    year=1991,
                    genres=["Rock"],
                    styles=["Indie"],
                ),
            ],
        )
        conn.execute(
            """
            INSERT INTO spotify_mapping(discogs_release_id, spotify_album_id, confidence, last_checked_at, is_override)
            VALUES (?, ?, ?, ?, ?)
            """,
            (101, "spotify:album:101", 0.9, "2026-01-01T00:00:00Z", 0),
        )
        conn.commit()
    finally:
        conn.close()

    selected = run_spin_release(genres=["Rock"], unmatched=True, seed=1)
    assert selected["discogs_release_id"] == 102


def test_spin_raises_when_no_matches(isolated_xdg):
    with pytest.raises(NoReleasesFoundError):
        run_spin_release(q="this-does-not-exist")


def test_spin_year_validation_error(isolated_xdg):
    with pytest.raises(ValueError):
        run_spin_release(year=":")
