from __future__ import annotations

import pytest

from discogs_player.data.db import get_connection
from discogs_player.data.repo import get_spotify_mapping, upsert_releases
from discogs_player.services.matching import MatchingResult
from discogs_player.use_cases import ensure_mapping


class _FakeSpotifyClient:
    def __init__(self, access_token: str):
        self.access_token = access_token


class _FakeMatchingService:
    def __init__(self, spotify_client, *, threshold: float = 0.72, search_limit: int = 10):
        _ = (spotify_client, threshold, search_limit)

    def match_release(self, release: dict[str, object]) -> MatchingResult:
        release_id = int(release["discogs_release_id"])
        if release_id == 1:
            return MatchingResult(
                matched=True,
                discogs_release_id=1,
                spotify_album_id="album-1",
                confidence=0.94,
                best_candidate={"id": "album-1", "name": "Nevermind"},
                candidates=[{"id": "album-1", "name": "Nevermind", "confidence": 0.94}],
            )

        return MatchingResult(
            matched=False,
            discogs_release_id=release_id,
            spotify_album_id=None,
            confidence=0.41,
            best_candidate={"id": "candidate-low", "name": "Low Match"},
            candidates=[{"id": "candidate-low", "name": "Low Match", "confidence": 0.41}],
        )


def _release(release_id: int, *, artist: str, title: str, year: int) -> dict[str, object]:
    return {
        "discogs_release_id": release_id,
        "artist": artist,
        "title": title,
        "year": year,
        "genres": ["Rock"],
        "styles": ["Alternative"],
        "thumb_url": None,
        "cover_url": None,
        "added_at": "2026-01-01T00:00:00Z",
        "last_synced_at": "2026-01-01T00:00:00Z",
        "is_active": 1,
    }


def test_run_match_release_persists_mapping(isolated_xdg, monkeypatch):
    conn = get_connection()
    try:
        upsert_releases(conn, [_release(1, artist="Nirvana", title="Nevermind", year=1991)])
    finally:
        conn.close()

    monkeypatch.setattr(ensure_mapping, "get_spotify_access_token", lambda conn=None: "token")
    monkeypatch.setattr(ensure_mapping, "SpotifyClient", _FakeSpotifyClient)
    monkeypatch.setattr(ensure_mapping, "MatchingService", _FakeMatchingService)

    result = ensure_mapping.run_match_release(1, threshold=0.7)

    assert result["matched"] is True
    assert result["spotify_album_id"] == "album-1"

    conn = get_connection()
    try:
        mapping = get_spotify_mapping(conn, 1)
    finally:
        conn.close()

    assert mapping is not None
    assert mapping["spotify_album_id"] == "album-1"
    assert mapping["is_override"] is False


def test_run_match_unmatched_batch_summary(isolated_xdg, monkeypatch):
    conn = get_connection()
    try:
        upsert_releases(
            conn,
            [
                _release(1, artist="Nirvana", title="Nevermind", year=1991),
                _release(2, artist="Pixies", title="Doolittle", year=1989),
            ],
        )
    finally:
        conn.close()

    monkeypatch.setattr(ensure_mapping, "get_spotify_access_token", lambda conn=None: "token")
    monkeypatch.setattr(ensure_mapping, "SpotifyClient", _FakeSpotifyClient)
    monkeypatch.setattr(ensure_mapping, "MatchingService", _FakeMatchingService)

    summary = ensure_mapping.run_match_unmatched(limit=10)

    assert summary["processed_count"] == 2
    assert summary["matched_count"] == 1
    assert len(summary["results"]) == 2


def test_run_match_override_and_preserve_override(isolated_xdg, monkeypatch):
    conn = get_connection()
    try:
        upsert_releases(conn, [_release(3, artist="U2", title="Boy", year=1980)])
    finally:
        conn.close()

    override = ensure_mapping.run_match_override(3, "spotify:album:boy123")
    assert override["spotify_album_id"] == "boy123"
    assert override["is_override"] is True

    class _ShouldNotBeCalledMatchingService(_FakeMatchingService):
        def match_release(self, release):  # pragma: no cover - this should never execute
            raise AssertionError("match_release should not run for override mappings")

    monkeypatch.setattr(ensure_mapping, "get_spotify_access_token", lambda conn=None: "token")
    monkeypatch.setattr(ensure_mapping, "SpotifyClient", _FakeSpotifyClient)
    monkeypatch.setattr(ensure_mapping, "MatchingService", _ShouldNotBeCalledMatchingService)

    result = ensure_mapping.run_match_release(3)
    assert result["source"] == "override"
    assert result["spotify_album_id"] == "boy123"
    assert result["matched"] is True


def test_run_match_override_accepts_open_spotify_album_url(isolated_xdg):
    conn = get_connection()
    try:
        upsert_releases(conn, [_release(4, artist="Blur", title="Parklife", year=1994)])
    finally:
        conn.close()

    result = ensure_mapping.run_match_override(
        4,
        "https://open.spotify.com/album/4Z8W4fKeB5YxbusRsdQVPb?si=abc123",
    )
    assert result["spotify_album_id"] == "4Z8W4fKeB5YxbusRsdQVPb"


def test_run_match_override_rejects_invalid_album_id(isolated_xdg):
    conn = get_connection()
    try:
        upsert_releases(conn, [_release(5, artist="The Cure", title="Disintegration", year=1989)])
    finally:
        conn.close()

    with pytest.raises(ValueError):
        ensure_mapping.run_match_override(5, "spotify:album:bad-id!")
