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


def test_matching_service_penalizes_cover_and_tribute_variants():
    release = {
        "discogs_release_id": 3,
        "artist": "Nirvana",
        "title": "Nevermind",
        "year": 1991,
    }
    candidates = [
        {
            "id": "cover-1",
            "name": "Nevermind (Piano Covers)",
            "artists": ["Nirvana Tribute Orchestra"],
            "release_date": "1991-01-01",
        }
    ]

    client = _FakeSpotifySearchClient(candidates)
    service = MatchingService(client, threshold=0.72)
    result = service.match_release(release)

    assert result.matched is False
    assert result.spotify_album_id is None
    assert result.confidence < 0.72


def test_matching_service_prefers_canonical_title_over_edition_noise():
    release = {
        "discogs_release_id": 4,
        "artist": "Nirvana",
        "title": "Nevermind",
        "year": 1991,
    }
    candidates = [
        {
            "id": "edition-1",
            "name": "Nevermind (Deluxe Remastered Edition)",
            "artists": ["Nirvana"],
            "release_date": "2011-01-01",
        },
        {
            "id": "canonical-1",
            "name": "Nevermind",
            "artists": ["Nirvana"],
            "release_date": "1991-09-24",
        },
    ]

    client = _FakeSpotifySearchClient(candidates)
    service = MatchingService(client, threshold=0.72)
    result = service.match_release(release)

    assert result.matched is True
    assert result.spotify_album_id == "canonical-1"
    assert result.best_candidate is not None
    assert result.best_candidate["id"] == "canonical-1"


def test_matching_service_penalizes_various_artists_false_positive():
    release = {
        "discogs_release_id": 5,
        "artist": "Radiohead",
        "title": "Kid A",
        "year": 2000,
    }
    candidates = [
        {
            "id": "various-1",
            "name": "Kid A",
            "artists": ["Various Artists"],
            "release_date": "2000-01-01",
        },
        {
            "id": "radiohead-1",
            "name": "Kid A",
            "artists": ["Radiohead"],
            "release_date": "2000-10-02",
        },
    ]

    client = _FakeSpotifySearchClient(candidates)
    service = MatchingService(client, threshold=0.72)
    result = service.match_release(release)

    assert result.matched is True
    assert result.spotify_album_id == "radiohead-1"


def test_matching_service_prefers_album_over_remix_single_with_same_base_title():
    release = {
        "discogs_release_id": 6,
        "artist": "Beck",
        "title": "Colors",
        "year": 2017,
    }
    candidates = [
        {
            "id": "album-1",
            "name": "Colors",
            "artists": ["Beck"],
            "release_date": "2017-10-13",
            "album_type": "album",
            "total_tracks": 11,
        },
        {
            "id": "single-remix-1",
            "name": "Colors (Picard Brothers Remix)",
            "artists": ["Beck"],
            "release_date": "2018-08-03",
            "album_type": "single",
            "total_tracks": 1,
        },
    ]

    client = _FakeSpotifySearchClient(candidates)
    service = MatchingService(client, threshold=0.72)
    result = service.match_release(release)

    assert result.matched is True
    assert result.best_candidate is not None
    assert result.best_candidate["id"] == "album-1"
    assert result.spotify_album_id == "album-1"
    assert result.candidates[0]["id"] == "album-1"
    assert result.candidates[1]["id"] == "single-remix-1"
    assert result.candidates[0]["confidence"] > result.candidates[1]["confidence"]


def test_matching_service_avoids_auto_high_confidence_for_remix_single_variant():
    release = {
        "discogs_release_id": 7,
        "artist": "Beck",
        "title": "Colors",
        "year": 2017,
    }
    candidates = [
        {
            "id": "single-remix-1",
            "name": "Colors (Picard Brothers Remix)",
            "artists": ["Beck"],
            "release_date": "2018-08-03",
            "album_type": "single",
            "total_tracks": 1,
        }
    ]

    client = _FakeSpotifySearchClient(candidates)
    service = MatchingService(client, threshold=0.90)
    result = service.match_release(release)

    assert result.matched is False
    assert result.spotify_album_id is None
    assert result.confidence < 0.90
