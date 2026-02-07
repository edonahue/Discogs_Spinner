from __future__ import annotations

from discogs_player.use_cases import spin_flow


def test_run_spin_action_returns_selected_release(monkeypatch):
    monkeypatch.setattr(
        spin_flow,
        "run_spin_release",
        lambda **kwargs: {
            "discogs_release_id": 123,
            "artist": "Nirvana",
            "title": "Nevermind",
            "year": 1991,
        },
    )

    payload = spin_flow.run_spin_action(
        q="nirvana",
        year="1990:1999",
        genres=["Rock"],
        styles=["Grunge"],
        unmatched=True,
        seed=42,
    )

    assert payload["action"] == "spin"
    assert payload["discogs_release_id"] == 123
    assert "Spin selected #123: Nirvana - Nevermind (1991) [seed=42]" == payload["status_message"]


def test_run_spin_action_reports_random_seed(monkeypatch):
    monkeypatch.setattr(
        spin_flow,
        "run_spin_release",
        lambda **kwargs: {
            "discogs_release_id": 9,
            "artist": "Artist",
            "title": "Album",
            "year": None,
        },
    )

    payload = spin_flow.run_spin_action(seed=None)
    assert payload["discogs_release_id"] == 9
    assert "[seed=random]" in str(payload["status_message"])


def test_run_play_last_spin_action_started(monkeypatch):
    monkeypatch.setattr(
        spin_flow,
        "run_play_release",
        lambda **kwargs: {
            "discogs_release_id": 55,
            "spotify_album_id": "album-55",
            "playback_started": True,
            "device_name": "Desk",
            "device_id": "desk-1",
        },
    )

    payload = spin_flow.run_play_last_spin_action()
    assert payload["playback_started"] is True
    assert payload["status_message"] == "Playing last spin on Desk: album-55"


def test_run_play_last_spin_action_fallback(monkeypatch):
    monkeypatch.setattr(
        spin_flow,
        "run_play_release",
        lambda **kwargs: {
            "discogs_release_id": 11,
            "spotify_album_id": None,
            "playback_started": False,
            "message": "No mapping.",
            "fallback_open_url": "https://open.spotify.com/search/test",
        },
    )

    payload = spin_flow.run_play_last_spin_action()
    assert payload["playback_started"] is False
    assert (
        payload["status_message"]
        == "No mapping. Open URL: https://open.spotify.com/search/test"
    )

