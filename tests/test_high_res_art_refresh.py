from __future__ import annotations

from discogs_player.core.settings import set_setting
from discogs_player.data.db import get_connection
from discogs_player.data.repo import upsert_releases, upsert_wantlist_entries
from discogs_player.services.high_res_art import HIGH_RES_ART_TARGET_SIZE_SETTING
from discogs_player.use_cases import high_res_art_refresh


def _release(release_id: int, *, cover_url: str) -> dict[str, object]:
    return {
        "discogs_release_id": release_id,
        "artist": "Artist",
        "title": f"Album {release_id}",
        "year": 2020,
        "genres": ["Rock"],
        "styles": ["Indie"],
        "thumb_url": "https://example.test/thumb.jpg",
        "cover_url": cover_url,
        "added_at": "2026-01-01T00:00:00Z",
        "last_synced_at": "2026-01-01T00:00:00Z",
        "is_active": 1,
    }


def _wantlist(release_id: int, *, cover_url: str) -> dict[str, object]:
    return {
        "discogs_release_id": release_id,
        "artist": "Want Artist",
        "title": f"Want {release_id}",
        "year": 2021,
        "genres": ["Electronic"],
        "styles": ["House"],
        "thumb_url": "https://example.test/thumb.jpg",
        "cover_url": cover_url,
        "notes": "",
        "added_at": "2026-01-01T00:00:00Z",
        "last_synced_at": "2026-01-01T00:00:00Z",
        "is_active": 1,
    }


def test_run_refresh_high_res_art_dry_run_counts_candidates(monkeypatch, isolated_xdg):
    conn = get_connection()
    try:
        upsert_releases(
            conn,
            [
                _release(
                    1,
                    cover_url=(
                        "https://i.discogs.com/a/rs:fit/h:600/w:600/format:webp/"
                        "discogs-images/R-1.jpg"
                    ),
                ),
                _release(2, cover_url="https://images.example.com/cover-2.jpg"),
            ],
        )
        upsert_wantlist_entries(
            conn,
            [
                _wantlist(
                    3,
                    cover_url=(
                        "https://i.discogs.com/b/rs:fit/h:600/w:600/format:webp/"
                        "discogs-images/R-3.jpg"
                    ),
                )
            ],
        )
    finally:
        conn.close()

    calls = {"count": 0}

    def _fake_fetch(url: str | None) -> str | None:
        if url:
            calls["count"] += 1
        return "/tmp/unused.img"

    monkeypatch.setattr(high_res_art_refresh, "get_or_fetch_cover_path", _fake_fetch)

    result = high_res_art_refresh.run_refresh_high_res_art(
        scope="both",
        target_size=1200,
        dry_run=True,
    )

    assert result["scanned_count"] == 3
    assert result["eligible_count"] == 2
    assert result["unique_upgraded_url_count"] == 2
    assert result["warmed_url_count"] == 0
    assert result["failed_url_count"] == 0
    assert result["warmed_release_count"] == 0
    assert result["collection_scanned_count"] == 2
    assert result["wantlist_scanned_count"] == 1
    assert calls["count"] == 0


def test_run_refresh_high_res_art_warms_unique_urls_only(monkeypatch, isolated_xdg):
    shared_cover_url = (
        "https://i.discogs.com/shared/rs:fit/h:600/w:600/format:webp/"
        "discogs-images/R-shared.jpg"
    )
    conn = get_connection()
    try:
        upsert_releases(
            conn,
            [
                _release(11, cover_url=shared_cover_url),
                _release(12, cover_url=shared_cover_url),
            ],
        )
    finally:
        conn.close()

    calls = {"count": 0}

    def _fake_fetch(url: str | None) -> str | None:
        if not url:
            return None
        calls["count"] += 1
        return "/tmp/high-res-shared.img"

    monkeypatch.setattr(high_res_art_refresh, "get_or_fetch_cover_path", _fake_fetch)

    result = high_res_art_refresh.run_refresh_high_res_art(
        scope="collection",
        target_size=1200,
        dry_run=False,
    )

    assert result["scanned_count"] == 2
    assert result["eligible_count"] == 2
    assert result["unique_upgraded_url_count"] == 1
    assert result["warmed_url_count"] == 1
    assert result["failed_url_count"] == 0
    assert result["warmed_release_count"] == 2
    assert calls["count"] == 1


def test_run_refresh_high_res_art_uses_configured_target_size(monkeypatch, isolated_xdg):
    set_setting(HIGH_RES_ART_TARGET_SIZE_SETTING, "1400")

    conn = get_connection()
    try:
        upsert_releases(
            conn,
            [
                _release(
                    21,
                    cover_url=(
                        "https://i.discogs.com/a/rs:fit/h:600/w:600/format:webp/"
                        "discogs-images/R-21.jpg"
                    ),
                )
            ],
        )
    finally:
        conn.close()

    captured_urls: list[str] = []

    def _fake_fetch(url: str | None) -> str | None:
        if not url:
            return None
        captured_urls.append(url)
        return "/tmp/high-res-1400.img"

    monkeypatch.setattr(high_res_art_refresh, "get_or_fetch_cover_path", _fake_fetch)

    result = high_res_art_refresh.run_refresh_high_res_art(
        scope="collection",
        target_size=None,
        dry_run=False,
    )

    assert result["target_size"] == 1400
    assert captured_urls
    assert "/h:1400/w:1400/" in captured_urls[0]


def test_run_refresh_high_res_art_falls_back_to_original_for_signed_discogs_urls(
    monkeypatch, isolated_xdg
):
    signed_url = (
        "https://i.discogs.com/hash/rs:fit/g:sm/q:90/h:600/w:600/"
        "czM6Ly9kaXNjb2dzLWRhdGFiYXNlLWltYWdlcy9SLTk5OS5qcGVn.jpeg"
    )
    conn = get_connection()
    try:
        upsert_releases(conn, [_release(999, cover_url=signed_url)])
    finally:
        conn.close()

    captured_urls: list[str] = []

    def _fake_fetch(url: str | None) -> str | None:
        if url:
            captured_urls.append(url)
        return "/tmp/signed-fallback.img"

    monkeypatch.setattr(high_res_art_refresh, "get_or_fetch_cover_path", _fake_fetch)

    result = high_res_art_refresh.run_refresh_high_res_art(
        scope="collection",
        target_size=1400,
        dry_run=False,
    )

    assert result["eligible_count"] == 0
    assert result["unique_upgraded_url_count"] == 0
    assert result["fallback_original_url_count"] == 1
    assert result["unique_candidate_url_count"] == 1
    assert result["warmed_url_count"] == 1
    assert captured_urls == [signed_url]
