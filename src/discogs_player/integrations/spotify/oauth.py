"""Spotify OAuth/token helpers for headless CLI use."""

from __future__ import annotations

import os
import secrets
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable
from urllib.parse import parse_qs, urlencode, urlparse

from discogs_player.core.settings import get_setting, set_setting

SPOTIFY_ACCESS_TOKEN_ENV = "SPOTIFY_ACCESS_TOKEN"
SPOTIFY_REFRESH_TOKEN_ENV = "SPOTIFY_REFRESH_TOKEN"
SPOTIFY_CLIENT_ID_ENV = "SPOTIFY_CLIENT_ID"
SPOTIFY_SECRET_ENV = "SPOTIFY_SECRET"
SPOTIFY_CLIENT_SECRET_LEGACY_ENV = "SPOTIFY_CLIENT_SECRET"
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_CALLBACK_PATH = "/callback"
SPOTIFY_KEYRING_SERVICE = "discogs_player"
SPOTIFY_ACCESS_TOKEN_KEY = "spotify_access_token"
SPOTIFY_REFRESH_TOKEN_KEY = "spotify_refresh_token"
SPOTIFY_CLIENT_SECRET_KEY = "spotify_client_secret"
SPOTIFY_DEFAULT_SCOPES = [
    "user-read-playback-state",
    "user-modify-playback-state",
    "user-read-currently-playing",
]


class SpotifyOAuthError(Exception):
    """Base class for Spotify OAuth errors."""


class SpotifyDependencyError(SpotifyOAuthError):
    """Raised when required Python dependency for Spotify integration is missing."""


class SpotifyAuthError(SpotifyOAuthError):
    """Raised for missing/invalid Spotify credentials or token refresh failures."""


class SpotifyOAuthTimeoutError(SpotifyAuthError):
    """Raised when local callback OAuth flow times out."""


def _load_dotenv_if_available() -> None:
    try:
        from dotenv import load_dotenv
    except ModuleNotFoundError:
        return
    load_dotenv()


def _httpx() -> Any:
    try:
        import httpx
    except ModuleNotFoundError as exc:
        raise SpotifyDependencyError(
            "Missing Python dependency: httpx. Install with `pip install -r requirements.txt`."
        ) from exc
    return httpx


def _keyring_module():
    try:
        import keyring
    except ModuleNotFoundError:
        return None
    except Exception:
        return None
    return keyring


def _keyring_get(name: str) -> str | None:
    keyring_module = _keyring_module()
    if keyring_module is None:
        return None
    try:
        value = keyring_module.get_password(SPOTIFY_KEYRING_SERVICE, name)
    except Exception:
        return None
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def _keyring_set(name: str, value: str) -> bool:
    keyring_module = _keyring_module()
    if keyring_module is None:
        return False
    try:
        keyring_module.set_password(SPOTIFY_KEYRING_SERVICE, name, value)
        return True
    except Exception:
        return False


def _int_or_none(raw: str | None) -> int | None:
    if raw is None:
        return None
    raw = raw.strip()
    if not raw:
        return None
    if not raw.isdigit():
        return None
    return int(raw)


def _env_client_secret() -> str | None:
    for key in (SPOTIFY_SECRET_ENV, SPOTIFY_CLIENT_SECRET_LEGACY_ENV):
        value = str(os.environ.get(key) or "").strip()
        if value:
            return value
    return None


def _read_secret(key: str, conn=None) -> str | None:
    from_keyring = _keyring_get(key)
    if from_keyring:
        # Mirror keyring secrets into app settings so desktop/system runtime
        # and venv runtime can share Spotify credentials consistently.
        try:
            set_setting(key, from_keyring, conn=conn)
        except Exception:
            pass
        return from_keyring

    from_settings = get_setting(key, conn=conn)
    if not isinstance(from_settings, str):
        return None
    from_settings = from_settings.strip()
    return from_settings or None


def _write_secret(key: str, value: str, conn=None) -> None:
    # Always keep a settings copy as a portability fallback across runtimes.
    set_setting(key, value, conn=conn)
    _keyring_set(key, value)


def _mirror_keyring_secrets_to_settings(conn=None) -> None:
    for key in (
        SPOTIFY_ACCESS_TOKEN_KEY,
        SPOTIFY_REFRESH_TOKEN_KEY,
        SPOTIFY_CLIENT_SECRET_KEY,
    ):
        value = _keyring_get(key)
        if not value:
            continue
        try:
            set_setting(key, value, conn=conn)
        except Exception:
            continue


def _refresh_spotify_access_token(
    *,
    refresh_token: str,
    client_id: str,
    client_secret: str,
    timeout_seconds: float = 30.0,
) -> tuple[str, int, str | None]:
    httpx_module = _httpx()

    try:
        response = httpx_module.post(
            SPOTIFY_TOKEN_URL,
            data={"grant_type": "refresh_token", "refresh_token": refresh_token},
            auth=(client_id, client_secret),
            timeout=timeout_seconds,
        )
    except Exception as exc:
        if isinstance(exc, httpx_module.RequestError):
            raise SpotifyAuthError(
                f"Spotify token refresh request failed: {exc}"
            ) from exc
        raise

    if response.status_code >= 400:
        detail = response.text[:240]
        raise SpotifyAuthError(
            f"Spotify token refresh failed ({response.status_code}): {detail}"
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise SpotifyAuthError(
            "Spotify token refresh response was not valid JSON"
        ) from exc

    access_token = payload.get("access_token")
    expires_in = payload.get("expires_in")
    returned_refresh_token = payload.get("refresh_token")

    if not isinstance(access_token, str) or not access_token:
        raise SpotifyAuthError("Spotify token refresh did not return access_token")

    expires_value = int(expires_in) if isinstance(expires_in, int) else 3600

    if returned_refresh_token is not None and not isinstance(
        returned_refresh_token, str
    ):
        returned_refresh_token = None

    return access_token, expires_value, returned_refresh_token


def _exchange_spotify_authorization_code(
    *,
    code: str,
    redirect_uri: str,
    client_id: str,
    client_secret: str,
    timeout_seconds: float = 30.0,
) -> tuple[str, int, str | None]:
    httpx_module = _httpx()

    try:
        response = httpx_module.post(
            SPOTIFY_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
            },
            auth=(client_id, client_secret),
            timeout=timeout_seconds,
        )
    except Exception as exc:
        if isinstance(exc, httpx_module.RequestError):
            raise SpotifyAuthError(
                f"Spotify authorization-code exchange failed: {exc}"
            ) from exc
        raise

    if response.status_code >= 400:
        detail = response.text[:240]
        detail_lower = detail.lower()
        if "redirect uri" in detail_lower or "redirect_uri" in detail_lower:
            raise SpotifyAuthError(
                "Spotify rejected redirect URI. In Spotify Developer Dashboard, add "
                f"exactly {redirect_uri} and retry authorization."
            )
        raise SpotifyAuthError(
            f"Spotify authorization-code exchange failed ({response.status_code}): {detail}"
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise SpotifyAuthError(
            "Spotify authorization-code exchange response was not valid JSON"
        ) from exc

    access_token = payload.get("access_token")
    expires_in = payload.get("expires_in")
    refresh_token = payload.get("refresh_token")

    if not isinstance(access_token, str) or not access_token:
        raise SpotifyAuthError(
            "Spotify authorization response did not return access_token"
        )

    expires_value = int(expires_in) if isinstance(expires_in, int) else 3600
    if refresh_token is not None and not isinstance(refresh_token, str):
        refresh_token = None

    return access_token, expires_value, refresh_token


def _normalize_scopes(scopes: list[str] | tuple[str, ...] | None) -> list[str]:
    if not scopes:
        return list(SPOTIFY_DEFAULT_SCOPES)

    normalized: list[str] = []
    seen: set[str] = set()
    for scope in scopes:
        value = str(scope or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return normalized or list(SPOTIFY_DEFAULT_SCOPES)


def _build_spotify_authorize_url(
    *,
    client_id: str,
    redirect_uri: str,
    state: str,
    scopes: list[str] | tuple[str, ...] | None = None,
) -> str:
    scope_values = _normalize_scopes(scopes)
    query = urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(scope_values),
            "state": state,
        }
    )
    return f"{SPOTIFY_AUTH_URL}?{query}"


def _first_query_value(params: dict[str, list[str]], key: str) -> str | None:
    values = params.get(key)
    if not values:
        return None
    value = str(values[0]).strip()
    return value or None


def _parse_callback_payload(
    raw_value: str,
) -> tuple[str | None, str | None, str | None, str | None] | None:
    value = str(raw_value or "").strip()
    if not value:
        return None

    query: str | None = None
    if "://" in value:
        query = urlparse(value).query
    elif "?" in value:
        query = value.split("?", 1)[1]
    elif value.startswith("?"):
        query = value[1:]
    elif value.startswith("code=") or value.startswith("error="):
        query = value

    if not query:
        return None

    params = parse_qs(query)
    code = _first_query_value(params, "code")
    state = _first_query_value(params, "state")
    error = _first_query_value(params, "error")
    error_description = _first_query_value(params, "error_description")

    if not code and not state and not error:
        return None
    return code, state, error, error_description


def _extract_manual_authorization_code(
    *,
    expected_state: str,
    manual_callback_url: str | None = None,
    manual_code: str | None = None,
    manual_input: str | None = None,
) -> tuple[str, str]:
    callback_value = str(manual_callback_url or "").strip()
    code_value = str(manual_code or "").strip()
    input_value = str(manual_input or "").strip()

    if callback_value:
        payload = _parse_callback_payload(callback_value)
        if payload is None:
            raise SpotifyAuthError(
                "Manual callback URL must include Spotify callback query values (code/state)."
            )
        code, state, error, error_description = payload
        if error:
            if error_description:
                raise SpotifyAuthError(
                    f"Spotify authorization error: {error} ({error_description})"
                )
            raise SpotifyAuthError(f"Spotify authorization error: {error}")
        if not state:
            raise SpotifyAuthError(
                "Manual callback URL is missing OAuth state. Paste the full redirect URL."
            )
        if state != expected_state:
            raise SpotifyAuthError(
                "Spotify OAuth state mismatch detected. Retry authorization."
            )
        if not code:
            raise SpotifyAuthError(
                "Manual callback URL did not include an authorization code."
            )
        return code, "manual_callback_url"

    if code_value:
        return code_value, "manual_code"

    if input_value:
        payload = _parse_callback_payload(input_value)
        if payload is None:
            return input_value, "manual_input_code"
        code, state, error, error_description = payload
        if error:
            if error_description:
                raise SpotifyAuthError(
                    f"Spotify authorization error: {error} ({error_description})"
                )
            raise SpotifyAuthError(f"Spotify authorization error: {error}")
        if state and state != expected_state:
            raise SpotifyAuthError(
                "Spotify OAuth state mismatch detected. Retry authorization."
            )
        if not code:
            raise SpotifyAuthError(
                "Manual authorization input did not include an authorization code."
            )
        return code, "manual_input_callback"

    raise SpotifyAuthError(
        "Manual Spotify OAuth entry requires callback URL, authorization code, or manual input."
    )


def _await_spotify_callback_code(
    *,
    listen_host: str,
    listen_port: int,
    expected_state: str,
    callback_path: str = SPOTIFY_CALLBACK_PATH,
    timeout_seconds: int = 180,
) -> str:
    result: dict[str, str | None] = {
        "code": None,
        "state": None,
        "error": None,
        "error_description": None,
    }
    received_event = threading.Event()

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path != callback_path:
                body = b"Not found."
                self.send_response(404)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            params = parse_qs(parsed.query)
            result["code"] = _first_query_value(params, "code")
            result["state"] = _first_query_value(params, "state")
            result["error"] = _first_query_value(params, "error")
            result["error_description"] = _first_query_value(
                params, "error_description"
            )

            if result["error"]:
                text = "Spotify authorization failed. You can close this window."
            elif result["state"] != expected_state:
                text = (
                    "Spotify authorization state mismatch. You can close this window."
                )
            elif result["code"]:
                text = "Spotify authorization received. You can close this window."
            else:
                text = "Spotify authorization callback missing code. You can close this window."

            body = text.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            received_event.set()

        def log_message(self, format: str, *args: object) -> None:  # noqa: A003
            _ = (format, args)
            return

    try:
        server = HTTPServer((listen_host, listen_port), CallbackHandler)
    except OSError as exc:
        raise SpotifyAuthError(
            f"Unable to bind local Spotify callback server at {listen_host}:{listen_port}: {exc}"
        ) from exc

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        if not received_event.wait(timeout=max(1, int(timeout_seconds))):
            raise SpotifyOAuthTimeoutError(
                "Timed out waiting for Spotify OAuth callback. Retry and complete authorization in browser."
            )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2.0)

    if result["error"]:
        description = result["error_description"]
        if description:
            raise SpotifyAuthError(
                f"Spotify authorization error: {result['error']} ({description})"
            )
        raise SpotifyAuthError(f"Spotify authorization error: {result['error']}")

    if result["state"] != expected_state:
        raise SpotifyAuthError(
            "Spotify OAuth state mismatch detected. Retry authorization."
        )

    code = result["code"]
    if not code:
        raise SpotifyAuthError(
            "Spotify OAuth callback did not include an authorization code."
        )

    return code


def run_spotify_oauth_login(
    *,
    listen_host: str = "127.0.0.1",
    listen_port: int = 8765,
    timeout_seconds: int = 180,
    scopes: list[str] | tuple[str, ...] | None = None,
    open_browser: bool = False,
    manual_mode: bool = False,
    manual_callback_url: str | None = None,
    manual_code: str | None = None,
    allow_manual_fallback: bool = False,
    on_authorization_url: Callable[[str], None] | None = None,
    on_manual_authorization_input: Callable[[], str] | None = None,
    conn=None,
) -> dict[str, object]:
    """Run one-time Spotify OAuth authorization-code flow."""
    _load_dotenv_if_available()

    client_id = os.environ.get(SPOTIFY_CLIENT_ID_ENV) or get_setting(
        "spotify_client_id", conn=conn
    )
    if not client_id:
        raise SpotifyAuthError(
            "Spotify client id is required. Set SPOTIFY_CLIENT_ID or store spotify_client_id in config."
        )

    client_secret = _env_client_secret() or _read_secret(
        SPOTIFY_CLIENT_SECRET_KEY,
        conn=conn,
    )
    if not client_secret:
        raise SpotifyAuthError(
            "Spotify client secret is required. Set SPOTIFY_SECRET "
            "(legacy: SPOTIFY_CLIENT_SECRET), or store spotify_client_secret in config."
        )

    callback_path = SPOTIFY_CALLBACK_PATH
    redirect_uri = f"http://{listen_host}:{int(listen_port)}{callback_path}"
    state = secrets.token_urlsafe(24)
    scope_values = _normalize_scopes(scopes)
    authorization_url = _build_spotify_authorize_url(
        client_id=client_id,
        redirect_uri=redirect_uri,
        state=state,
        scopes=scope_values,
    )

    if on_authorization_url is not None:
        on_authorization_url(authorization_url)

    opened_browser = False
    if open_browser:
        try:
            opened_browser = bool(
                webbrowser.open(authorization_url, new=1, autoraise=True)
            )
        except Exception:
            opened_browser = False

    manual_requested = bool(
        manual_mode
        or str(manual_callback_url or "").strip()
        or str(manual_code or "").strip()
    )
    code_source = "local_callback"
    manual_fallback_used = False

    if manual_requested:
        manual_input = None
        if not str(manual_callback_url or "").strip() and not str(
            manual_code or ""
        ).strip():
            if on_manual_authorization_input is None:
                raise SpotifyAuthError(
                    "Manual Spotify OAuth mode requires callback URL, authorization code, "
                    "or a manual input prompt callback."
                )
            manual_input = on_manual_authorization_input()

        code, code_source = _extract_manual_authorization_code(
            expected_state=state,
            manual_callback_url=manual_callback_url,
            manual_code=manual_code,
            manual_input=manual_input,
        )
    else:
        try:
            code = _await_spotify_callback_code(
                listen_host=listen_host,
                listen_port=int(listen_port),
                expected_state=state,
                callback_path=callback_path,
                timeout_seconds=int(timeout_seconds),
            )
        except SpotifyAuthError as exc:
            if (
                not allow_manual_fallback
                or on_manual_authorization_input is None
                or not (
                    isinstance(exc, SpotifyOAuthTimeoutError)
                    or str(exc).startswith(
                        "Unable to bind local Spotify callback server"
                    )
                )
            ):
                raise

            manual_input = on_manual_authorization_input()
            code, code_source = _extract_manual_authorization_code(
                expected_state=state,
                manual_input=manual_input,
            )
            manual_fallback_used = True

    access_token, expires_in, refresh_token = _exchange_spotify_authorization_code(
        code=code,
        redirect_uri=redirect_uri,
        client_id=client_id,
        client_secret=client_secret,
    )

    now_epoch = int(time.time())
    _write_secret(SPOTIFY_ACCESS_TOKEN_KEY, access_token, conn=conn)
    set_setting(
        "spotify_access_token_expires_at",
        str(now_epoch + max(1, int(expires_in))),
        conn=conn,
    )

    if refresh_token:
        _write_secret(SPOTIFY_REFRESH_TOKEN_KEY, refresh_token, conn=conn)

    set_setting("spotify_client_id", client_id, conn=conn)
    _write_secret(SPOTIFY_CLIENT_SECRET_KEY, client_secret, conn=conn)

    stored_refresh_token = bool(
        refresh_token
        or os.environ.get(SPOTIFY_REFRESH_TOKEN_ENV)
        or _read_secret(SPOTIFY_REFRESH_TOKEN_KEY, conn=conn)
    )

    return {
        "ok": True,
        "listen_host": listen_host,
        "listen_port": int(listen_port),
        "redirect_uri": redirect_uri,
        "scopes": scope_values,
        "authorization_url": authorization_url,
        "open_browser_requested": bool(open_browser),
        "open_browser_succeeded": bool(opened_browser),
        "manual_mode_requested": bool(manual_requested),
        "manual_fallback_used": bool(manual_fallback_used),
        "authorization_code_source": code_source,
        "access_token_expires_in": int(expires_in),
        "received_refresh_token": bool(refresh_token),
        "stored_refresh_token": stored_refresh_token,
    }


def get_spotify_auth_diagnostics(
    *,
    listen_host: str = "127.0.0.1",
    listen_port: int = 8765,
    conn=None,
) -> dict[str, object]:
    """Return Spotify auth readiness diagnostics with no secret values."""
    _load_dotenv_if_available()

    now_epoch = int(time.time())

    env_client_id_present = bool(str(os.environ.get(SPOTIFY_CLIENT_ID_ENV) or "").strip())
    env_secret_primary_present = bool(str(os.environ.get(SPOTIFY_SECRET_ENV) or "").strip())
    env_secret_legacy_present = bool(
        str(os.environ.get(SPOTIFY_CLIENT_SECRET_LEGACY_ENV) or "").strip()
    )
    env_secret_present = bool(env_secret_primary_present or env_secret_legacy_present)
    env_refresh_present = bool(str(os.environ.get(SPOTIFY_REFRESH_TOKEN_ENV) or "").strip())
    env_access_present = bool(str(os.environ.get(SPOTIFY_ACCESS_TOKEN_ENV) or "").strip())

    stored_client_id_present = bool(
        str(get_setting("spotify_client_id", conn=conn) or "").strip()
    )
    stored_secret_present = bool(_read_secret(SPOTIFY_CLIENT_SECRET_KEY, conn=conn))
    stored_refresh_present = bool(_read_secret(SPOTIFY_REFRESH_TOKEN_KEY, conn=conn))
    stored_access_present = bool(_read_secret(SPOTIFY_ACCESS_TOKEN_KEY, conn=conn))

    expires_at_raw = get_setting("spotify_access_token_expires_at", conn=conn)
    expires_at = _int_or_none(expires_at_raw)
    access_token_fresh = bool(
        env_access_present
        or (
            stored_access_present
            and (expires_at is None or expires_at > now_epoch + 60)
        )
    )
    access_token_expires_in_seconds = (
        None if expires_at is None else int(expires_at - now_epoch)
    )

    client_id_available = bool(env_client_id_present or stored_client_id_present)
    client_secret_available = bool(env_secret_present or stored_secret_present)
    refresh_token_available = bool(env_refresh_present or stored_refresh_present)

    configured = has_spotify_configuration(conn=conn)
    keyring_available = _keyring_module() is not None
    expected_redirect_uri = f"http://{listen_host}:{int(listen_port)}{SPOTIFY_CALLBACK_PATH}"
    redirect_uri_setup_hint = (
        "If browser shows INVALID_CLIENT or Invalid redirect URI, add this exact URI "
        f"in Spotify Developer Dashboard Redirect URIs: {expected_redirect_uri}"
    )

    diagnosis = "ready"
    if configured:
        diagnosis = "ready"
        recommended_action = "Run `dplayer devices --json` or `./scripts/spotify_live_smoke.sh`."
    elif not client_id_available or not client_secret_available:
        diagnosis = "missing_credentials"
        recommended_action = (
            "Set SPOTIFY_CLIENT_ID and SPOTIFY_SECRET, then run "
            "`dplayer auth spotify --open-browser --manual`."
        )
    elif refresh_token_available:
        diagnosis = "verify_token_device_access"
        recommended_action = (
            "Credentials look present; run `dplayer auth spotify-doctor --probe-devices` "
            "to verify token/device access."
        )
    else:
        diagnosis = "needs_oauth_connect"
        recommended_action = (
            "Run `dplayer auth spotify --open-browser --listen-host 127.0.0.1 "
            "--listen-port 8765` to complete OAuth and store refresh token."
        )

    return {
        "configured": bool(configured),
        "diagnosis": diagnosis,
        "keyring_available": bool(keyring_available),
        "expected_redirect_uri": expected_redirect_uri,
        "redirect_uri_setup_hint": redirect_uri_setup_hint,
        "recommended_action": recommended_action,
        "credentials": {
            "client_id_available": bool(client_id_available),
            "client_secret_available": bool(client_secret_available),
            "refresh_token_available": bool(refresh_token_available),
            "client_id_sources": {
                "env": bool(env_client_id_present),
                "stored": bool(stored_client_id_present),
            },
            "client_secret_sources": {
                "env_spotify_secret": bool(env_secret_primary_present),
                "env_spotify_client_secret_legacy": bool(env_secret_legacy_present),
                "stored": bool(stored_secret_present),
            },
            "refresh_token_sources": {
                "env": bool(env_refresh_present),
                "stored": bool(stored_refresh_present),
            },
        },
        "access_token": {
            "available": bool(env_access_present or stored_access_present),
            "fresh": bool(access_token_fresh),
            "source_env": bool(env_access_present),
            "source_stored": bool(stored_access_present),
            "expires_at_epoch": expires_at,
            "expires_in_seconds": access_token_expires_in_seconds,
        },
    }


def has_spotify_configuration(conn=None) -> bool:
    """Return True when Spotify auth credentials/tokens are configured."""
    _load_dotenv_if_available()
    _mirror_keyring_secrets_to_settings(conn=conn)

    env_token = str(os.environ.get(SPOTIFY_ACCESS_TOKEN_ENV) or "").strip()
    if env_token:
        return True

    stored_token = _read_secret(SPOTIFY_ACCESS_TOKEN_KEY, conn=conn)
    expires_at_raw = get_setting("spotify_access_token_expires_at", conn=conn)
    expires_at = _int_or_none(expires_at_raw)
    now_epoch = int(time.time())
    if stored_token and (expires_at is None or expires_at > now_epoch + 60):
        return True

    refresh_token = str(
        os.environ.get(SPOTIFY_REFRESH_TOKEN_ENV)
        or _read_secret(SPOTIFY_REFRESH_TOKEN_KEY, conn=conn)
        or ""
    ).strip()
    client_id = str(
        os.environ.get(SPOTIFY_CLIENT_ID_ENV)
        or get_setting("spotify_client_id", conn=conn)
        or ""
    ).strip()
    client_secret = str(
        _env_client_secret() or _read_secret(SPOTIFY_CLIENT_SECRET_KEY, conn=conn)
        or ""
    ).strip()
    return bool(refresh_token and client_id and client_secret)


def get_spotify_access_token(conn=None) -> str:
    """Resolve Spotify access token from env, stored settings, or refresh flow."""
    _load_dotenv_if_available()
    _mirror_keyring_secrets_to_settings(conn=conn)

    env_token = os.environ.get(SPOTIFY_ACCESS_TOKEN_ENV)
    if env_token:
        return env_token.strip()

    stored_token = _read_secret(SPOTIFY_ACCESS_TOKEN_KEY, conn=conn)
    expires_at_raw = get_setting("spotify_access_token_expires_at", conn=conn)
    expires_at = _int_or_none(expires_at_raw)

    now_epoch = int(time.time())
    if stored_token and (expires_at is None or expires_at > now_epoch + 60):
        return stored_token

    refresh_token = os.environ.get(SPOTIFY_REFRESH_TOKEN_ENV) or _read_secret(
        SPOTIFY_REFRESH_TOKEN_KEY, conn=conn
    )
    client_id = os.environ.get(SPOTIFY_CLIENT_ID_ENV) or get_setting(
        "spotify_client_id", conn=conn
    )
    client_secret = _env_client_secret() or _read_secret(
        SPOTIFY_CLIENT_SECRET_KEY,
        conn=conn,
    )

    if refresh_token and client_id and client_secret:
        token, expires_in, returned_refresh_token = _refresh_spotify_access_token(
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret,
        )
        _write_secret(SPOTIFY_ACCESS_TOKEN_KEY, token, conn=conn)
        set_setting(
            "spotify_access_token_expires_at",
            str(now_epoch + max(1, expires_in)),
            conn=conn,
        )
        if returned_refresh_token:
            _write_secret(SPOTIFY_REFRESH_TOKEN_KEY, returned_refresh_token, conn=conn)
        return token

    if stored_token:
        return stored_token

    raise SpotifyAuthError(
        "Spotify access token not configured. Set SPOTIFY_ACCESS_TOKEN, or configure "
        "SPOTIFY_CLIENT_ID/SPOTIFY_SECRET (legacy: SPOTIFY_CLIENT_SECRET)/"
        "SPOTIFY_REFRESH_TOKEN "
        "for auto-refresh."
    )
