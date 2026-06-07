"""Use-cases for Spotify device listing and default device selection."""

from __future__ import annotations

from discogs_player.capabilities import get_player_backend
from discogs_player.core.settings import get_setting, set_setting
from discogs_player.data.db import get_connection


class NoSpotifyDevicesError(RuntimeError):
    """Raised when no Spotify playback devices are available."""


def _score_device(device: dict[str, object]) -> int:
    score = 0

    if device.get("id"):
        score += 5
    else:
        score -= 1000

    if device.get("is_active"):
        score += 100

    if not device.get("is_restricted"):
        score += 20

    device_type = str(device.get("type") or "").lower()
    if "computer" in device_type:
        score += 30
    elif "speaker" in device_type:
        score += 10

    name = str(device.get("name") or "").lower()
    for hint in ("desktop", "computer", "linux", "pc"):
        if hint in name:
            score += 10

    return score


def choose_auto_device(devices: list[dict[str, object]]) -> dict[str, object]:
    if not devices:
        raise NoSpotifyDevicesError(
            "No Spotify devices found. Open Spotify on at least one device."
        )

    with_ids = [device for device in devices if device.get("id")]
    if not with_ids:
        raise NoSpotifyDevicesError(
            "Spotify returned devices without ids; cannot set default device."
        )

    unrestricted = [d for d in with_ids if not d.get("is_restricted")]
    candidates = unrestricted if unrestricted else with_ids

    return max(
        candidates,
        key=lambda device: (
            _score_device(device),
            str(device.get("name") or ""),
            str(device.get("id") or ""),
        ),
    )


def run_list_devices() -> list[dict[str, object]]:
    backend = get_player_backend()
    conn = get_connection()
    try:
        default_device_id = get_setting("default_spotify_device_id", conn=conn)
        devices = backend.list_devices(conn=conn)
    finally:
        conn.close()

    for device in devices:
        device["is_default"] = bool(
            default_device_id and device.get("id") == default_device_id
        )
    return devices


def run_set_default_device(device_id: str) -> dict[str, str | None]:
    normalized_id = device_id.strip()
    if not normalized_id:
        raise ValueError("Device id cannot be empty.")

    backend = get_player_backend()
    conn = get_connection()
    try:
        devices = backend.list_devices(conn=conn)

        selected = None
        for device in devices:
            if device.get("id") == normalized_id:
                selected = device
                break

        if selected is None:
            raise ValueError(f"Spotify device '{normalized_id}' was not found.")

        name = str(selected.get("name") or "") or None
        set_setting("default_spotify_device_id", normalized_id, conn=conn)
        set_setting("default_spotify_device_name", name, conn=conn)
    finally:
        conn.close()

    return {"id": normalized_id, "name": name}


def run_auto_set_default_device() -> dict[str, str | None]:
    backend = get_player_backend()
    conn = get_connection()
    try:
        devices = backend.list_devices(conn=conn)
        selected = choose_auto_device(devices)

        selected_id = str(selected.get("id"))
        selected_name = str(selected.get("name") or "") or None

        set_setting("default_spotify_device_id", selected_id, conn=conn)
        set_setting("default_spotify_device_name", selected_name, conn=conn)
    finally:
        conn.close()

    return {"id": selected_id, "name": selected_name}


def run_get_default_device() -> dict[str, str | None]:
    conn = get_connection()
    try:
        return {
            "id": get_setting("default_spotify_device_id", conn=conn),
            "name": get_setting("default_spotify_device_name", conn=conn),
        }
    finally:
        conn.close()
