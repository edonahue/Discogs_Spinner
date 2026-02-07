from __future__ import annotations

from discogs_player.services.matching import MatchingService


class _FakeSpotifySearchClient:
    def __init__(self, rows: list[dict[str, object]]):
        self.rows = rows
        self.queries: list[str] = []

    def search_albums(self, *, query: str, limit: int = 10) -> list[dict[str, object]]:
        _ = limit
        self.queries.append(query)
        return list(self.rows)


def test_matching_service_selects_best_candidate():
    release = {
        "discogs_release_id": 1,
        "artist": "Nirvana",
        "title": "Nevermind",
        "year": 1991,
    }

    candidates = [
        {
            "id": "wrong-1",
            "name": "Never Mind The Bollocks",
            "artists": ["Sex Pistols"],
            "release_date": "1977-01-01",
            "uri": "spotify:album:wrong-1",
            "external_url": "https://open.spotify.com/album/wrong-1",
        },
        {
            "id": "best-1",
            "name": "Nevermind",
            "artists": ["Nirvana"],
            "release_date": "1991-09-24",
            "uri": "spotify:album:best-1",
            "external_url": "https://open.spotify.com/album/best-1",
        },
    ]

    client = _FakeSpotifySearchClient(candidates)
    service = MatchingService(client, threshold=0.70)

    result = service.match_release(release)

    assert result.matched is True
    assert result.spotify_album_id == "best-1"
    assert result.confidence >= 0.70
    assert result.best_candidate is not None
    assert result.best_candidate["id"] == "best-1"
    assert len(result.candidates) >= 1
    assert client.queries


def test_matching_service_returns_unmatched_when_confidence_low():
    release = {
        "discogs_release_id": 2,
        "artist": "The Clash",
        "title": "London Calling",
        "year": 1979,
    }

    candidates = [
        {
            "id": "off-1",
            "name": "Random Ambient Collection",
            "artists": ["Various"],
            "release_date": "2019-01-01",
            "uri": "spotify:album:off-1",
            "external_url": "https://open.spotify.com/album/off-1",
        }
    ]

    client = _FakeSpotifySearchClient(candidates)
    service = MatchingService(client, threshold=0.85)

    result = service.match_release(release)

    assert result.matched is False
    assert result.spotify_album_id is None
    assert result.confidence < 0.85
