from __future__ import annotations

import time
from urllib.parse import parse_qs, urlparse

import pytest

from discogs_player.core.settings import get_setting, set_setting
from discogs_player.data.db import get_connection
from discogs_player.services import spotify_oauth


class _FakeKeyring:
    def __init__(self, initial: dict[str, str] | None = None):
        self.store = dict(initial or {})

    def get_password(self, service: str, name: str) -> str | None:
        _ = service
        return self.store.get(name)

    def set_password(self, service: str, name: str, value: str) -> None:
        _ = service
        self.store[name] = value


def test_get_spotify_access_token_uses_keyring_token_when_valid(isolated_xdg, monkeypatch):
    fake_keyring = _FakeKeyring({"spotify_access_token": "keyring-token"})
    monkeypatch.setattr(spotify_oauth, "_keyring_module", lambda: fake_keyring)
    monkeypatch.delenv("SPOTIFY_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("SPOTIFY_REFRESH_TOKEN", raising=False)
    monkeypatch.delenv("SPOTIFY_CLIENT_ID", raising=False)
    monkeypatch.delenv("SPOTIFY_CLIENT_SECRET", raising=False)

    conn = get_connection()
    try:
        set_setting("spotify_access_token_expires_at", str(int(time.time()) + 3600), conn=conn)
    finally:
        conn.close()

    token = spotify_oauth.get_spotify_access_token()
    assert token == "keyring-token"


def test_get_spotify_access_token_refresh_stores_to_keyring(isolated_xdg, monkeypatch):
    fake_keyring = _FakeKeyring()
    monkeypatch.setattr(spotify_oauth, "_keyring_module", lambda: fake_keyring)
    monkeypatch.delenv("SPOTIFY_ACCESS_TOKEN", raising=False)
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "client-id")
    monkeypatch.setenv("SPOTIFY_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("SPOTIFY_REFRESH_TOKEN", "refresh-old")
    monkeypatch.setattr(
        spotify_oauth,
        "_refresh_spotify_access_token",
        lambda **kwargs: ("access-new", 1200, "refresh-new"),
    )

    token = spotify_oauth.get_spotify_access_token()

    assert token == "access-new"
    assert fake_keyring.store["spotify_access_token"] == "access-new"
    assert fake_keyring.store["spotify_refresh_token"] == "refresh-new"

    conn = get_connection()
    try:
        expires_at = get_setting("spotify_access_token_expires_at", conn=conn)
        stored_plain_access = get_setting("spotify_access_token", conn=conn)
    finally:
        conn.close()

    assert expires_at is not None
    assert stored_plain_access is None


def test_build_spotify_authorize_url_contains_expected_params():
    url = spotify_oauth._build_spotify_authorize_url(
        client_id="client-1",
        redirect_uri="http://127.0.0.1:8765/callback",
        state="state-abc",
        scopes=["user-read-playback-state", "user-modify-playback-state"],
    )
    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    assert parsed.scheme == "https"
    assert parsed.netloc == "accounts.spotify.com"
    assert parsed.path == "/authorize"
    assert params["response_type"] == ["code"]
    assert params["client_id"] == ["client-1"]
    assert params["redirect_uri"] == ["http://127.0.0.1:8765/callback"]
    assert params["state"] == ["state-abc"]
    assert params["scope"] == ["user-read-playback-state user-modify-playback-state"]


def test_run_spotify_oauth_login_happy_path(isolated_xdg, monkeypatch):
    fake_keyring = _FakeKeyring()
    monkeypatch.setattr(spotify_oauth, "_keyring_module", lambda: fake_keyring)
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "client-xyz")
    monkeypatch.setenv("SPOTIFY_CLIENT_SECRET", "secret-xyz")
    monkeypatch.delenv("SPOTIFY_REFRESH_TOKEN", raising=False)

    seen_callback: dict[str, object] = {}

    def _fake_wait_for_code(**kwargs):
        seen_callback.update(kwargs)
        return "code-123"

    seen_exchange: dict[str, object] = {}

    def _fake_exchange(**kwargs):
        seen_exchange.update(kwargs)
        return ("access-123", 1800, "refresh-123")

    monkeypatch.setattr(spotify_oauth, "_await_spotify_callback_code", _fake_wait_for_code)
    monkeypatch.setattr(spotify_oauth, "_exchange_spotify_authorization_code", _fake_exchange)

    urls: list[str] = []
    result = spotify_oauth.run_spotify_oauth_login(
        listen_host="127.0.0.1",
        listen_port=8765,
        timeout_seconds=120,
        open_browser=False,
        on_authorization_url=urls.append,
    )

    assert urls and urls[0].startswith("https://accounts.spotify.com/authorize?")
    assert seen_callback["listen_port"] == 8765
    assert seen_exchange["code"] == "code-123"
    assert result["received_refresh_token"] is True
    assert result["stored_refresh_token"] is True
    assert result["access_token_expires_in"] == 1800
    assert fake_keyring.store["spotify_access_token"] == "access-123"
    assert fake_keyring.store["spotify_refresh_token"] == "refresh-123"
    assert fake_keyring.store["spotify_client_secret"] == "secret-xyz"


def test_run_spotify_oauth_login_requires_client_credentials(isolated_xdg, monkeypatch):
    fake_keyring = _FakeKeyring()
    monkeypatch.setattr(spotify_oauth, "_keyring_module", lambda: fake_keyring)
    monkeypatch.delenv("SPOTIFY_CLIENT_ID", raising=False)
    monkeypatch.delenv("SPOTIFY_CLIENT_SECRET", raising=False)

    conn = get_connection()
    try:
        set_setting("spotify_client_id", None, conn=conn)
        set_setting("spotify_client_secret", None, conn=conn)
    finally:
        conn.close()

    with pytest.raises(spotify_oauth.SpotifyAuthError, match="client id"):
        spotify_oauth.run_spotify_oauth_login()

