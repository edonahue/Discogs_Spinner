"""Use-case for starting Spotify playback for a Discogs release."""

from __future__ import annotations

from urllib.parse import quote

from discogs_player.core.settings import get_int_setting, get_setting, set_setting
from discogs_player.data.db import get_connection
from discogs_player.data.repo import get_release_by_id, get_spotify_mapping
from discogs_player.services.spotify_client import SpotifyApiError, SpotifyClient, SpotifyPlaybackError
from discogs_player.services.spotify_oauth import SpotifyAuthError, get_spotify_access_token
from discogs_player.use_cases.ensure_mapping import run_match_release
from discogs_player.use_cases.device_management import choose_auto_device


class MissingLastSpinError(RuntimeError):
    """Raised when --last-spin is requested without a stored last spin release id."""


class MissingSpotifyMappingError(RuntimeError):
    """Raised when no spotify_mapping exists for the selected Discogs release."""


class NoPlayableDeviceError(RuntimeError):
    """Raised when playback cannot find or infer a usable Spotify device."""


def _spotify_album_open_url(spotify_album_id: str | None) -> str | None:
    if not spotify_album_id:
        return None
    normalized = spotify_album_id.strip().removeprefix("spotify:album:")
    if not normalized:
        return None
    return f"https://open.spotify.com/album/{normalized}"


def _spotify_search_url(release: dict[str, object]) -> str:
    artist = str(release.get("artist") or "").strip()
    title = str(release.get("title") or "").strip()
    query = " ".join(part for part in (artist, title) if part)
    if not query:
        return "https://open.spotify.com/search"
    return f"https://open.spotify.com/search/{quote(query)}"


def _build_result(
    *,
    discogs_release_id: int,
    spotify_album_id: str | None,
    device_id: str | None,
    device_name: str | None,
    used_last_spin: bool,
    auto_match_attempted: bool,
    auto_matched: bool,
    playback_started: bool,
    fallback_open_url: str | None = None,
    fallback_reason: str | None = None,
    message: str | None = None,
) -> dict[str, object]:
    return {
        "discogs_release_id": discogs_release_id,
        "spotify_album_id": spotify_album_id,
        "spotify_open_url": _spotify_album_open_url(spotify_album_id),
        "device_id": device_id,
        "device_name": device_name,
        "used_last_spin": used_last_spin,
        "auto_match_attempted": auto_match_attempted,
        "auto_matched": auto_matched,
        "playback_started": playback_started,
        "fallback_open_url": fallback_open_url,
        "fallback_reason": fallback_reason,
        "message": message,
    }


def _resolve_discogs_release_id(
    *,
    discogs_release_id: int | None,
    use_last_spin: bool,
    conn,
) -> int:
    if discogs_release_id is not None and use_last_spin:
        raise ValueError("Provide a release id or --last-spin, not both.")

    if use_last_spin:
        last_spin = get_int_setting("last_spin_release_id", conn=conn)
        if last_spin is None:
            raise MissingLastSpinError(
                "No last spin release id is stored. Run `dplayer spin` first or pass a release id."
            )
        return last_spin

    if discogs_release_id is None:
        raise ValueError("Provide <discogs_release_id> or use --last-spin.")

    return discogs_release_id


def _get_spotify_album_id(conn, discogs_release_id: int) -> str | None:
    row = get_spotify_mapping(conn, discogs_release_id)
    if row is None:
        return None

    album_id = str(row.get("spotify_album_id") or "").strip()
    if not album_id:
        return None

    return album_id


def run_play_release(
    *,
    discogs_release_id: int | None = None,
    use_last_spin: bool = False,
    auto_match: bool = False,
    open_fallback: bool = False,
) -> dict[str, object]:
    conn = get_connection()
    try:
        resolved_release_id = _resolve_discogs_release_id(
            discogs_release_id=discogs_release_id,
            use_last_spin=use_last_spin,
            conn=conn,
        )
        release = get_release_by_id(conn, resolved_release_id)
        if release is None:
            raise ValueError(f"Discogs release {resolved_release_id} was not found in local database.")

        auto_match_attempted = False
        auto_matched = False
        spotify_album_id = _get_spotify_album_id(conn, resolved_release_id)
        if not spotify_album_id and auto_match:
            auto_match_attempted = True
            try:
                match_result = run_match_release(resolved_release_id)
            except (SpotifyAuthError, SpotifyApiError) as exc:
                if open_fallback:
                    return _build_result(
                        discogs_release_id=resolved_release_id,
                        spotify_album_id=None,
                        device_id=None,
                        device_name=None,
                        used_last_spin=bool(use_last_spin),
                        auto_match_attempted=True,
                        auto_matched=False,
                        playback_started=False,
                        fallback_open_url=_spotify_search_url(release),
                        fallback_reason="auto_match_error",
                        message=f"Auto-match failed: {exc}",
                    )
                raise
            matched_album_id = str(match_result.get("spotify_album_id") or "").strip()
            if match_result.get("matched") and matched_album_id:
                spotify_album_id = matched_album_id
                auto_matched = True

        if not spotify_album_id:
            message = (
                f"No Spotify mapping found for Discogs release {resolved_release_id}. "
                "Run `dplayer match` first."
            )
            if auto_match_attempted:
                message = (
                    f"No Spotify mapping found for Discogs release {resolved_release_id}. "
                    "Auto-match did not find a confident result; run `dplayer match` manually."
                )

            if open_fallback:
                return _build_result(
                    discogs_release_id=resolved_release_id,
                    spotify_album_id=None,
                    device_id=None,
                    device_name=None,
                    used_last_spin=bool(use_last_spin),
                    auto_match_attempted=auto_match_attempted,
                    auto_matched=auto_matched,
                    playback_started=False,
                    fallback_open_url=_spotify_search_url(release),
                    fallback_reason="missing_mapping",
                    message=message,
                )

            raise MissingSpotifyMappingError(message)

        try:
            token = get_spotify_access_token(conn=conn)
            client = SpotifyClient(access_token=token)
            devices = client.list_devices()
        except (SpotifyAuthError, SpotifyApiError) as exc:
            if open_fallback:
                reason = "auth_error" if isinstance(exc, SpotifyAuthError) else "api_error"
                return _build_result(
                    discogs_release_id=resolved_release_id,
                    spotify_album_id=spotify_album_id,
                    device_id=None,
                    device_name=None,
                    used_last_spin=bool(use_last_spin),
                    auto_match_attempted=auto_match_attempted,
                    auto_matched=auto_matched,
                    playback_started=False,
                    fallback_open_url=_spotify_album_open_url(spotify_album_id),
                    fallback_reason=reason,
                    message=str(exc),
                )
            raise

        default_device_id = get_setting("default_spotify_device_id", conn=conn)
        default_device_name = get_setting("default_spotify_device_name", conn=conn)

        chosen_device = None
        for device in devices:
            if default_device_id and device.get("id") == default_device_id:
                chosen_device = device
                break

        if chosen_device is None:
            if not devices:
                message = "No Spotify devices found. Open Spotify on one device before playing."
                if open_fallback:
                    return _build_result(
                        discogs_release_id=resolved_release_id,
                        spotify_album_id=spotify_album_id,
                        device_id=None,
                        device_name=None,
                        used_last_spin=bool(use_last_spin),
                        auto_match_attempted=auto_match_attempted,
                        auto_matched=auto_matched,
                        playback_started=False,
                        fallback_open_url=_spotify_album_open_url(spotify_album_id),
                        fallback_reason="no_device",
                        message=message,
                    )

                raise NoPlayableDeviceError(
                    message
                )
            chosen_device = choose_auto_device(devices)
            default_device_id = str(chosen_device.get("id"))
            default_device_name = str(chosen_device.get("name") or "") or None
            set_setting("default_spotify_device_id", default_device_id, conn=conn)
            set_setting("default_spotify_device_name", default_device_name, conn=conn)
        else:
            default_device_name = str(chosen_device.get("name") or "") or default_device_name
            set_setting("default_spotify_device_name", default_device_name, conn=conn)

        if default_device_id is None:
            message = "Unable to determine a Spotify device id for playback."
            if open_fallback:
                return _build_result(
                    discogs_release_id=resolved_release_id,
                    spotify_album_id=spotify_album_id,
                    device_id=None,
                    device_name=None,
                    used_last_spin=bool(use_last_spin),
                    auto_match_attempted=auto_match_attempted,
                    auto_matched=auto_matched,
                    playback_started=False,
                    fallback_open_url=_spotify_album_open_url(spotify_album_id),
                    fallback_reason="no_device",
                    message=message,
                )
            raise NoPlayableDeviceError(message)

        try:
            client.start_album_playback(spotify_album_id, device_id=default_device_id)
        except SpotifyPlaybackError as exc:
            if open_fallback:
                return _build_result(
                    discogs_release_id=resolved_release_id,
                    spotify_album_id=spotify_album_id,
                    device_id=default_device_id,
                    device_name=default_device_name,
                    used_last_spin=bool(use_last_spin),
                    auto_match_attempted=auto_match_attempted,
                    auto_matched=auto_matched,
                    playback_started=False,
                    fallback_open_url=_spotify_album_open_url(spotify_album_id),
                    fallback_reason="playback_error",
                    message=str(exc),
                )
            raise

        return _build_result(
            discogs_release_id=resolved_release_id,
            spotify_album_id=spotify_album_id,
            device_id=default_device_id,
            device_name=default_device_name,
            used_last_spin=bool(use_last_spin),
            auto_match_attempted=auto_match_attempted,
            auto_matched=auto_matched,
            playback_started=True,
        )
    finally:
        conn.close()
