"""Tests for YouTube search URL construction logic."""

from __future__ import annotations

import urllib.parse



def _build_youtube_search_url(artist: str, title: str, year: int | None) -> str:
    parts = [p for p in [artist, title, str(year) if year else None] if p]
    query = urllib.parse.quote_plus(" ".join(parts))
    return f"https://www.youtube.com/results?search_query={query}"


def test_url_base_is_youtube_search() -> None:
    url = _build_youtube_search_url("Radiohead", "OK Computer", 1997)
    assert url.startswith("https://www.youtube.com/results?search_query=")


def test_url_contains_artist_and_title() -> None:
    url = _build_youtube_search_url("Radiohead", "OK Computer", 1997)
    decoded = urllib.parse.unquote_plus(url.split("search_query=")[1])
    assert "Radiohead" in decoded
    assert "OK Computer" in decoded


def test_url_includes_year_when_present() -> None:
    url = _build_youtube_search_url("Radiohead", "OK Computer", 1997)
    decoded = urllib.parse.unquote_plus(url.split("search_query=")[1])
    assert "1997" in decoded


def test_url_omits_year_when_none() -> None:
    url = _build_youtube_search_url("Radiohead", "OK Computer", None)
    assert "None" not in url


def test_url_encodes_special_characters() -> None:
    url = _build_youtube_search_url("AC/DC", "Back in Black", 1980)
    # spaces encoded as +
    assert "+" in url or "%20" in url
    # slash encoded
    assert "/" not in url.split("search_query=")[1]
