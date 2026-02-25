from __future__ import annotations

import pytest

import discogs_player.integrations.spotify.spotify_client as spotify_client
from discogs_player.integrations.spotify.oauth import SpotifyAuthError
from discogs_player.integrations.spotify.spotify_client import SpotifyApiError, SpotifyClient


class _FakeResponse:
    def __init__(
        self,
        *,
        status_code: int,
        text: str = "",
        json_payload: object | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self.text = text
        self._json_payload = json_payload
        self.headers = headers or {}
        self.content = b"" if json_payload is None else b"x"

    def json(self) -> object:
        return self._json_payload


class _FakeHttpx:
    class RequestError(Exception):
        pass

    def __init__(self, responses: list[_FakeResponse]) -> None:
        self._responses = list(responses)
        self.calls = 0

    def request(self, *args, **kwargs):
        _ = (args, kwargs)
        self.calls += 1
        if not self._responses:
            raise AssertionError("No fake responses left for request().")
        return self._responses.pop(0)


def test_request_retries_429_with_retry_after(monkeypatch):
    fake_httpx = _FakeHttpx(
        [
            _FakeResponse(
                status_code=429,
                text="Too many requests",
                headers={"Retry-After": "1"},
            ),
            _FakeResponse(status_code=200, json_payload={"ok": True}),
        ]
    )
    sleep_calls: list[float] = []

    monkeypatch.setattr(spotify_client, "_httpx", lambda: fake_httpx)
    monkeypatch.setattr(
        spotify_client.time,
        "sleep",
        lambda seconds: sleep_calls.append(float(seconds)),
    )

    client = SpotifyClient(
        access_token="token",
        rate_limit_max_retries=2,
        rate_limit_backoff_seconds=5.0,
        rate_limit_jitter_seconds=0.0,
    )
    payload = client._request("GET", "/v1/search")

    assert payload == {"ok": True}
    assert fake_httpx.calls == 2
    assert sleep_calls == [1.0]


def test_request_retries_429_with_exponential_backoff(monkeypatch):
    fake_httpx = _FakeHttpx(
        [
            _FakeResponse(status_code=429, text="Too many requests"),
            _FakeResponse(status_code=429, text="Too many requests"),
            _FakeResponse(status_code=200, json_payload={"ok": True}),
        ]
    )
    sleep_calls: list[float] = []

    monkeypatch.setattr(spotify_client, "_httpx", lambda: fake_httpx)
    monkeypatch.setattr(
        spotify_client.time,
        "sleep",
        lambda seconds: sleep_calls.append(float(seconds)),
    )

    client = SpotifyClient(
        access_token="token",
        rate_limit_max_retries=3,
        rate_limit_backoff_seconds=2.0,
        rate_limit_max_sleep_seconds=30.0,
        rate_limit_jitter_seconds=0.0,
    )
    payload = client._request("GET", "/v1/search")

    assert payload == {"ok": True}
    assert fake_httpx.calls == 3
    assert sleep_calls == [2.0, 4.0]


def test_request_raises_after_429_retry_budget_exhausted(monkeypatch):
    fake_httpx = _FakeHttpx(
        [
            _FakeResponse(
                status_code=429,
                text="Too many requests",
                headers={"Retry-After": "1"},
            ),
            _FakeResponse(status_code=429, text="Too many requests"),
        ]
    )
    sleep_calls: list[float] = []

    monkeypatch.setattr(spotify_client, "_httpx", lambda: fake_httpx)
    monkeypatch.setattr(
        spotify_client.time,
        "sleep",
        lambda seconds: sleep_calls.append(float(seconds)),
    )

    client = SpotifyClient(
        access_token="token",
        rate_limit_max_retries=1,
        rate_limit_backoff_seconds=2.0,
        rate_limit_jitter_seconds=0.0,
    )

    with pytest.raises(SpotifyApiError, match="429"):
        client._request("GET", "/v1/search")

    assert fake_httpx.calls == 2
    assert sleep_calls == [1.0]


def test_request_raises_429_with_retry_after_hint_when_not_retrying(monkeypatch):
    fake_httpx = _FakeHttpx(
        [
            _FakeResponse(
                status_code=429,
                text="Too many requests",
                headers={"Retry-After": "77"},
            ),
        ]
    )
    monkeypatch.setattr(spotify_client, "_httpx", lambda: fake_httpx)

    client = SpotifyClient(
        access_token="token",
        rate_limit_max_retries=0,
        rate_limit_retry_after_cap_seconds=0.0,
        rate_limit_max_sleep_seconds=120.0,
        rate_limit_jitter_seconds=0.0,
    )

    with pytest.raises(SpotifyApiError, match=r"retry_after=77\.000s"):
        client._request("GET", "/v1/search")


def test_request_caps_retry_after_to_max_sleep_without_explicit_cap(monkeypatch):
    fake_httpx = _FakeHttpx(
        [
            _FakeResponse(
                status_code=429,
                text="Too many requests",
                headers={"Retry-After": "60"},
            ),
            _FakeResponse(status_code=200, json_payload={"ok": True}),
        ]
    )
    sleep_calls: list[float] = []

    monkeypatch.setattr(spotify_client, "_httpx", lambda: fake_httpx)
    monkeypatch.setattr(
        spotify_client.time,
        "sleep",
        lambda seconds: sleep_calls.append(float(seconds)),
    )

    client = SpotifyClient(
        access_token="token",
        rate_limit_max_retries=1,
        rate_limit_max_sleep_seconds=5.0,
        rate_limit_retry_after_cap_seconds=0.0,
        rate_limit_jitter_seconds=0.0,
    )
    payload = client._request("GET", "/v1/search")

    assert payload == {"ok": True}
    assert fake_httpx.calls == 2
    assert sleep_calls == [5.0]


def test_request_caps_retry_after_when_configured(monkeypatch):
    fake_httpx = _FakeHttpx(
        [
            _FakeResponse(
                status_code=429,
                text="Too many requests",
                headers={"Retry-After": "60"},
            ),
            _FakeResponse(status_code=200, json_payload={"ok": True}),
        ]
    )
    sleep_calls: list[float] = []

    monkeypatch.setattr(spotify_client, "_httpx", lambda: fake_httpx)
    monkeypatch.setattr(
        spotify_client.time,
        "sleep",
        lambda seconds: sleep_calls.append(float(seconds)),
    )

    client = SpotifyClient(
        access_token="token",
        rate_limit_max_retries=1,
        rate_limit_retry_after_cap_seconds=5.0,
        rate_limit_jitter_seconds=0.0,
    )
    payload = client._request("GET", "/v1/search")

    assert payload == {"ok": True}
    assert fake_httpx.calls == 2
    assert sleep_calls == [5.0]


def test_request_raises_429_with_capped_retry_after_hint(monkeypatch):
    fake_httpx = _FakeHttpx(
        [
            _FakeResponse(
                status_code=429,
                text="Too many requests",
                headers={"Retry-After": "120"},
            ),
        ]
    )
    monkeypatch.setattr(spotify_client, "_httpx", lambda: fake_httpx)

    client = SpotifyClient(
        access_token="token",
        rate_limit_max_retries=0,
        rate_limit_retry_after_cap_seconds=15.0,
        rate_limit_jitter_seconds=0.0,
    )

    with pytest.raises(
        SpotifyApiError,
        match=r"retry_after=15\.000s, header_retry_after=120\.000s",
    ):
        client._request("GET", "/v1/search")


def test_request_does_not_retry_auth_errors(monkeypatch):
    fake_httpx = _FakeHttpx([_FakeResponse(status_code=401, text="Unauthorized")])
    sleep_calls: list[float] = []

    monkeypatch.setattr(spotify_client, "_httpx", lambda: fake_httpx)
    monkeypatch.setattr(
        spotify_client.time,
        "sleep",
        lambda seconds: sleep_calls.append(float(seconds)),
    )

    client = SpotifyClient(access_token="token", rate_limit_max_retries=5)
    with pytest.raises(SpotifyAuthError):
        client._request("GET", "/v1/search")

    assert fake_httpx.calls == 1
    assert sleep_calls == []


def test_list_devices_fails_fast_on_429_when_playback_retries_disabled(monkeypatch):
    fake_httpx = _FakeHttpx(
        [
            _FakeResponse(
                status_code=429,
                text="Too many requests",
                headers={"Retry-After": "120"},
            ),
        ]
    )
    sleep_calls: list[float] = []

    monkeypatch.setattr(spotify_client, "_httpx", lambda: fake_httpx)
    monkeypatch.setattr(
        spotify_client.time,
        "sleep",
        lambda seconds: sleep_calls.append(float(seconds)),
    )

    client = SpotifyClient(
        access_token="token",
        rate_limit_max_retries=5,
        playback_rate_limit_max_retries=0,
        rate_limit_jitter_seconds=0.0,
    )
    with pytest.raises(SpotifyApiError, match="429"):
        client.list_devices()

    assert fake_httpx.calls == 1
    assert sleep_calls == []


def test_start_playback_uses_playback_retry_budget(monkeypatch):
    fake_httpx = _FakeHttpx(
        [
            _FakeResponse(
                status_code=429,
                text="Too many requests",
                headers={"Retry-After": "1"},
            ),
            _FakeResponse(status_code=204),
        ]
    )
    sleep_calls: list[float] = []

    monkeypatch.setattr(spotify_client, "_httpx", lambda: fake_httpx)
    monkeypatch.setattr(
        spotify_client.time,
        "sleep",
        lambda seconds: sleep_calls.append(float(seconds)),
    )

    client = SpotifyClient(
        access_token="token",
        rate_limit_max_retries=0,
        playback_rate_limit_max_retries=1,
        rate_limit_jitter_seconds=0.0,
    )
    client.start_album_playback("album-123", device_id="device-1")

    assert fake_httpx.calls == 2
    assert sleep_calls == [1.0]
