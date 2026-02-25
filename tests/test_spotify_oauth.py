from __future__ import annotations

import time
from urllib.parse import parse_qs, urlparse

import pytest

from discogs_player.core.settings import get_setting, set_setting
from discogs_player.data.db import get_connection
from discogs_player.integrations.spotify import oauth as spotify_oauth


class _FakeKeyring:
    def __init__(self, initial: dict[str, str] | None = None):
        self.store = dict(initial or {})

    def get_password(self, service: str, name: str) -> str | None:
        _ = service
        return self.store.get(name)

    def set_password(self, service: str, name: str, value: str) -> None:
        _ = service
        self.store[name] = value


def test_get_spotify_access_token_uses_keyring_token_when_valid(
    isolated_xdg, monkeypatch
):
    fake_keyring = _FakeKeyring({"spotify_access_token": "keyring-token"})
    monkeypatch.setattr(spotify_oauth, "_keyring_module", lambda: fake_keyring)
    monkeypatch.delenv("SPOTIFY_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("SPOTIFY_REFRESH_TOKEN", raising=False)
    monkeypatch.delenv("SPOTIFY_CLIENT_ID", raising=False)
    monkeypatch.delenv("SPOTIFY_CLIENT_SECRET", raising=False)

    conn = get_connection()
    try:
        set_setting(
            "spotify_access_token_expires_at", str(int(time.time()) + 3600), conn=conn
        )
    finally:
        conn.close()

    token = spotify_oauth.get_spotify_access_token()
    assert token == "keyring-token"
    conn = get_connection()
    try:
        assert get_setting("spotify_access_token", conn=conn) == "keyring-token"
    finally:
        conn.close()


def test_has_spotify_configuration_mirrors_keyring_refresh_credentials(
    isolated_xdg, monkeypatch
):
    fake_keyring = _FakeKeyring(
        {
            "spotify_access_token": "token-abc",
            "spotify_refresh_token": "refresh-abc",
            "spotify_client_secret": "secret-abc",
        }
    )
    monkeypatch.setattr(spotify_oauth, "_keyring_module", lambda: fake_keyring)
    monkeypatch.delenv("SPOTIFY_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("SPOTIFY_REFRESH_TOKEN", raising=False)
    monkeypatch.delenv("SPOTIFY_SECRET", raising=False)
    monkeypatch.delenv("SPOTIFY_CLIENT_SECRET", raising=False)

    conn = get_connection()
    try:
        set_setting(
            "spotify_access_token_expires_at", str(int(time.time()) + 3600), conn=conn
        )
        assert spotify_oauth.has_spotify_configuration(conn=conn) is True
        assert get_setting("spotify_refresh_token", conn=conn) == "refresh-abc"
        assert get_setting("spotify_client_secret", conn=conn) == "secret-abc"
    finally:
        conn.close()


def test_get_spotify_access_token_refresh_stores_to_keyring(isolated_xdg, monkeypatch):
    fake_keyring = _FakeKeyring()
    monkeypatch.setattr(spotify_oauth, "_keyring_module", lambda: fake_keyring)
    monkeypatch.delenv("SPOTIFY_ACCESS_TOKEN", raising=False)
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "client-id")
    monkeypatch.setenv("SPOTIFY_SECRET", "client-secret")
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
    assert stored_plain_access == "access-new"


def test_get_spotify_access_token_uses_legacy_client_secret_alias(
    isolated_xdg, monkeypatch
):
    fake_keyring = _FakeKeyring()
    monkeypatch.setattr(spotify_oauth, "_keyring_module", lambda: fake_keyring)
    monkeypatch.delenv("SPOTIFY_ACCESS_TOKEN", raising=False)
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "client-id")
    monkeypatch.delenv("SPOTIFY_SECRET", raising=False)
    monkeypatch.setenv("SPOTIFY_CLIENT_SECRET", "secret-alias")
    monkeypatch.setenv("SPOTIFY_REFRESH_TOKEN", "refresh-old")
    monkeypatch.setattr(
        spotify_oauth,
        "_refresh_spotify_access_token",
        lambda **kwargs: ("access-alias", 1200, None),
    )

    token = spotify_oauth.get_spotify_access_token()

    assert token == "access-alias"
    assert fake_keyring.store["spotify_access_token"] == "access-alias"


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
    monkeypatch.setenv("SPOTIFY_SECRET", "secret-xyz")
    monkeypatch.delenv("SPOTIFY_REFRESH_TOKEN", raising=False)

    seen_callback: dict[str, object] = {}

    def _fake_wait_for_code(**kwargs):
        seen_callback.update(kwargs)
        return "code-123"

    seen_exchange: dict[str, object] = {}

    def _fake_exchange(**kwargs):
        seen_exchange.update(kwargs)
        return ("access-123", 1800, "refresh-123")

    monkeypatch.setattr(
        spotify_oauth, "_await_spotify_callback_code", _fake_wait_for_code
    )
    monkeypatch.setattr(
        spotify_oauth, "_exchange_spotify_authorization_code", _fake_exchange
    )

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


def test_run_spotify_oauth_login_accepts_legacy_client_secret_alias(
    isolated_xdg, monkeypatch
):
    fake_keyring = _FakeKeyring()
    monkeypatch.setattr(spotify_oauth, "_keyring_module", lambda: fake_keyring)
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "client-xyz")
    monkeypatch.delenv("SPOTIFY_SECRET", raising=False)
    monkeypatch.setenv("SPOTIFY_CLIENT_SECRET", "secret-alias")

    monkeypatch.setattr(
        spotify_oauth, "_await_spotify_callback_code", lambda **kwargs: "code-abc"
    )
    monkeypatch.setattr(
        spotify_oauth,
        "_exchange_spotify_authorization_code",
        lambda **kwargs: ("access-abc", 1800, "refresh-abc"),
    )

    result = spotify_oauth.run_spotify_oauth_login(
        listen_host="127.0.0.1",
        listen_port=8765,
        timeout_seconds=120,
        open_browser=False,
    )

    assert result["ok"] is True
    assert fake_keyring.store["spotify_client_secret"] == "secret-alias"


def test_run_spotify_oauth_login_manual_callback_url_happy_path(
    isolated_xdg, monkeypatch
):
    fake_keyring = _FakeKeyring()
    monkeypatch.setattr(spotify_oauth, "_keyring_module", lambda: fake_keyring)
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "client-manual")
    monkeypatch.setenv("SPOTIFY_SECRET", "secret-manual")
    monkeypatch.setattr(spotify_oauth.secrets, "token_urlsafe", lambda _: "state-123")

    def _should_not_wait_for_callback(**kwargs):
        _ = kwargs
        raise AssertionError("Local callback server should not run in manual mode")

    seen_exchange: dict[str, object] = {}

    def _fake_exchange(**kwargs):
        seen_exchange.update(kwargs)
        return ("access-manual", 1800, "refresh-manual")

    monkeypatch.setattr(
        spotify_oauth, "_await_spotify_callback_code", _should_not_wait_for_callback
    )
    monkeypatch.setattr(
        spotify_oauth, "_exchange_spotify_authorization_code", _fake_exchange
    )

    result = spotify_oauth.run_spotify_oauth_login(
        manual_mode=True,
        manual_callback_url=(
            "http://127.0.0.1:8765/callback?code=manual-code-1&state=state-123"
        ),
        open_browser=False,
    )

    assert result["ok"] is True
    assert result["manual_mode_requested"] is True
    assert result["manual_fallback_used"] is False
    assert result["authorization_code_source"] == "manual_callback_url"
    assert seen_exchange["code"] == "manual-code-1"
    assert fake_keyring.store["spotify_access_token"] == "access-manual"


def test_run_spotify_oauth_login_uses_manual_fallback_on_timeout(
    isolated_xdg, monkeypatch
):
    fake_keyring = _FakeKeyring()
    monkeypatch.setattr(spotify_oauth, "_keyring_module", lambda: fake_keyring)
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "client-timeout")
    monkeypatch.setenv("SPOTIFY_SECRET", "secret-timeout")
    monkeypatch.setattr(spotify_oauth.secrets, "token_urlsafe", lambda _: "state-456")

    def _timeout_wait_for_code(**kwargs):
        _ = kwargs
        raise spotify_oauth.SpotifyOAuthTimeoutError("Timed out waiting for callback")

    monkeypatch.setattr(
        spotify_oauth, "_await_spotify_callback_code", _timeout_wait_for_code
    )
    monkeypatch.setattr(
        spotify_oauth,
        "_exchange_spotify_authorization_code",
        lambda **kwargs: ("access-fallback", 1200, "refresh-fallback"),
    )

    manual_prompts: list[str] = []

    def _manual_input() -> str:
        manual_prompts.append("prompted")
        return "http://127.0.0.1:8765/callback?code=fallback-code-1&state=state-456"

    result = spotify_oauth.run_spotify_oauth_login(
        allow_manual_fallback=True,
        on_manual_authorization_input=_manual_input,
        open_browser=False,
    )

    assert manual_prompts == ["prompted"]
    assert result["ok"] is True
    assert result["manual_mode_requested"] is False
    assert result["manual_fallback_used"] is True
    assert result["authorization_code_source"] == "manual_input_callback"
    assert fake_keyring.store["spotify_access_token"] == "access-fallback"


def test_run_spotify_oauth_login_manual_code_happy_path(isolated_xdg, monkeypatch):
    fake_keyring = _FakeKeyring()
    monkeypatch.setattr(spotify_oauth, "_keyring_module", lambda: fake_keyring)
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "client-code")
    monkeypatch.setenv("SPOTIFY_SECRET", "secret-code")

    def _should_not_wait_for_callback(**kwargs):
        _ = kwargs
        raise AssertionError("Local callback server should not run in manual mode")

    seen_exchange: dict[str, object] = {}

    def _fake_exchange(**kwargs):
        seen_exchange.update(kwargs)
        return ("access-code", 1800, "refresh-code")

    monkeypatch.setattr(
        spotify_oauth, "_await_spotify_callback_code", _should_not_wait_for_callback
    )
    monkeypatch.setattr(
        spotify_oauth, "_exchange_spotify_authorization_code", _fake_exchange
    )

    result = spotify_oauth.run_spotify_oauth_login(
        manual_mode=True,
        manual_code="manual-code-xyz",
        open_browser=False,
    )

    assert result["ok"] is True
    assert result["manual_mode_requested"] is True
    assert result["manual_fallback_used"] is False
    assert result["authorization_code_source"] == "manual_code"
    assert seen_exchange["code"] == "manual-code-xyz"
    assert fake_keyring.store["spotify_access_token"] == "access-code"


def test_has_spotify_configuration_uses_spotify_secret(
    isolated_xdg, monkeypatch
):
    monkeypatch.delenv("SPOTIFY_ACCESS_TOKEN", raising=False)
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "client-id")
    monkeypatch.delenv("SPOTIFY_CLIENT_SECRET", raising=False)
    monkeypatch.setenv("SPOTIFY_SECRET", "secret-primary")
    monkeypatch.setenv("SPOTIFY_REFRESH_TOKEN", "refresh-token")

    assert spotify_oauth.has_spotify_configuration() is True


def test_run_spotify_oauth_login_requires_client_credentials(isolated_xdg, monkeypatch):
    fake_keyring = _FakeKeyring()
    monkeypatch.setattr(spotify_oauth, "_keyring_module", lambda: fake_keyring)
    monkeypatch.delenv("SPOTIFY_CLIENT_ID", raising=False)
    monkeypatch.delenv("SPOTIFY_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("SPOTIFY_SECRET", raising=False)

    conn = get_connection()
    try:
        set_setting("spotify_client_id", None, conn=conn)
        set_setting("spotify_client_secret", None, conn=conn)
    finally:
        conn.close()

    with pytest.raises(spotify_oauth.SpotifyAuthError, match="client id"):
        spotify_oauth.run_spotify_oauth_login()


def test_get_spotify_auth_diagnostics_reports_missing_credentials(
    isolated_xdg, monkeypatch
):
    monkeypatch.setattr(spotify_oauth, "_keyring_module", lambda: None)
    monkeypatch.delenv("SPOTIFY_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("SPOTIFY_REFRESH_TOKEN", raising=False)
    monkeypatch.delenv("SPOTIFY_CLIENT_ID", raising=False)
    monkeypatch.delenv("SPOTIFY_SECRET", raising=False)
    monkeypatch.delenv("SPOTIFY_CLIENT_SECRET", raising=False)

    diagnostics = spotify_oauth.get_spotify_auth_diagnostics()

    assert diagnostics["configured"] is False
    assert diagnostics["diagnosis"] == "missing_credentials"
    assert diagnostics["credentials"]["client_id_available"] is False
    assert diagnostics["credentials"]["client_secret_available"] is False
    assert diagnostics["expected_redirect_uri"] == "http://127.0.0.1:8765/callback"
    assert "http://127.0.0.1:8765/callback" in diagnostics["redirect_uri_setup_hint"]
    assert "Set SPOTIFY_CLIENT_ID and SPOTIFY_SECRET" in diagnostics["recommended_action"]


def test_get_spotify_auth_diagnostics_reports_available_env_credentials(
    isolated_xdg, monkeypatch
):
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "client-id")
    monkeypatch.setenv("SPOTIFY_SECRET", "secret-id")
    monkeypatch.setenv("SPOTIFY_REFRESH_TOKEN", "refresh-id")
    monkeypatch.delenv("SPOTIFY_ACCESS_TOKEN", raising=False)

    diagnostics = spotify_oauth.get_spotify_auth_diagnostics(
        listen_host="localhost",
        listen_port=9999,
    )

    assert diagnostics["credentials"]["client_id_available"] is True
    assert diagnostics["credentials"]["client_secret_available"] is True
    assert diagnostics["credentials"]["refresh_token_available"] is True
    assert diagnostics["diagnosis"] == "ready"
    assert diagnostics["expected_redirect_uri"] == "http://localhost:9999/callback"
