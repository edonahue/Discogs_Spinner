"""Use-case for starting Spotify playback for a Discogs release."""

from __future__ import annotations

from discogs_player.core.settings import get_int_setting, get_setting, set_setting
from discogs_player.data.db import get_connection
from discogs_player.services.spotify_client import SpotifyClient
from discogs_player.services.spotify_oauth import get_spotify_access_token
from discogs_player.use_cases.device_management import choose_auto_device


class MissingLastSpinError(RuntimeError):
    """Raised when --last-spin is requested without a stored last spin release id."""


class MissingSpotifyMappingError(RuntimeError):
    """Raised when no spotify_mapping exists for the selected Discogs release."""


class NoPlayableDeviceError(RuntimeError):
    """Raised when playback cannot find or infer a usable Spotify device."""


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


def _get_spotify_album_id(conn, discogs_release_id: int) -> str:
    row = conn.execute(
        "SELECT spotify_album_id FROM spotify_mapping WHERE discogs_release_id = ?",
        (discogs_release_id,),
    ).fetchone()

    if row is None or not row["spotify_album_id"]:
        raise MissingSpotifyMappingError(
            f"No Spotify mapping found for Discogs release {discogs_release_id}. "
            "Run `dplayer match` first."
        )

    return str(row["spotify_album_id"])


def run_play_release(
    *,
    discogs_release_id: int | None = None,
    use_last_spin: bool = False,
) -> dict[str, object]:
    conn = get_connection()
    try:
        resolved_release_id = _resolve_discogs_release_id(
            discogs_release_id=discogs_release_id,
            use_last_spin=use_last_spin,
            conn=conn,
        )
        spotify_album_id = _get_spotify_album_id(conn, resolved_release_id)

        token = get_spotify_access_token(conn=conn)
        client = SpotifyClient(access_token=token)
        devices = client.list_devices()

        default_device_id = get_setting("default_spotify_device_id", conn=conn)
        default_device_name = get_setting("default_spotify_device_name", conn=conn)

        chosen_device = None
        for device in devices:
            if default_device_id and device.get("id") == default_device_id:
                chosen_device = device
                break

        if chosen_device is None:
            if not devices:
                raise NoPlayableDeviceError(
                    "No Spotify devices found. Open Spotify on one device before playing."
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
            raise NoPlayableDeviceError("Unable to determine a Spotify device id for playback.")

        client.start_album_playback(spotify_album_id, device_id=default_device_id)

        return {
            "discogs_release_id": resolved_release_id,
            "spotify_album_id": spotify_album_id,
            "device_id": default_device_id,
            "device_name": default_device_name,
            "used_last_spin": bool(use_last_spin),
        }
    finally:
        conn.close()
