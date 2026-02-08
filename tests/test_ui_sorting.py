from __future__ import annotations

from discogs_player.ui.sorting import sort_release_items


def _item(
    release_id: int,
    *,
    artist: str,
    title: str,
    year: int | None,
    genres: list[str] | None = None,
) -> dict[str, object]:
    return {
        "discogs_release_id": release_id,
        "artist": artist,
        "title": title,
        "year": year,
        "genres": genres or [],
    }


def test_sort_release_items_artist_title_default():
    rows = [
        _item(3, artist="miles davis", title="Kind of Blue", year=1959),
        _item(1, artist="Nirvana", title="Nevermind", year=1991),
        _item(2, artist="Aphex Twin", title="Selected Ambient Works 85-92", year=1992),
    ]
    sorted_rows = sort_release_items(rows, sort_mode="artist_title")
    assert [item["discogs_release_id"] for item in sorted_rows] == [2, 3, 1]


def test_sort_release_items_year_desc_and_year_asc():
    rows = [
        _item(1, artist="A", title="One", year=1991),
        _item(2, artist="B", title="Two", year=None),
        _item(3, artist="C", title="Three", year=1989),
        _item(4, artist="D", title="Four", year=2002),
    ]

    desc_rows = sort_release_items(rows, sort_mode="year_desc")
    asc_rows = sort_release_items(rows, sort_mode="year_asc")

    assert [item["discogs_release_id"] for item in desc_rows] == [4, 1, 3, 2]
    assert [item["discogs_release_id"] for item in asc_rows] == [3, 1, 4, 2]


def test_sort_release_items_genre_and_genre_year():
    rows = [
        _item(1, artist="B", title="First", year=1988, genres=["Rock"]),
        _item(2, artist="A", title="Second", year=1998, genres=["Electronic"]),
        _item(3, artist="C", title="Third", year=2002, genres=["Rock"]),
        _item(4, artist="D", title="Fourth", year=2010, genres=[]),
    ]

    genre_rows = sort_release_items(rows, sort_mode="genre")
    genre_year_rows = sort_release_items(rows, sort_mode="genre_year")

    assert [item["discogs_release_id"] for item in genre_rows] == [4, 2, 1, 3]
    assert [item["discogs_release_id"] for item in genre_year_rows] == [4, 2, 3, 1]


def test_sort_release_items_unknown_mode_falls_back_to_artist_title():
    rows = [
        _item(10, artist="ZZ Top", title="Eliminator", year=1983),
        _item(11, artist="ABBA", title="Gold", year=1992),
    ]
    sorted_rows = sort_release_items(rows, sort_mode="not-a-mode")
    assert [item["discogs_release_id"] for item in sorted_rows] == [11, 10]
