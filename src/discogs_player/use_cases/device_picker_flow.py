"""GUI-friendly wrappers for Spotify device picker actions."""

from __future__ import annotations

from discogs_player.use_cases.device_management import (
    run_auto_set_default_device,
    run_list_devices,
    run_set_default_device,
)


def _extract_default_device(
    devices: list[dict[str, object]],
) -> dict[str, object] | None:
    for device in devices:
        if device.get("is_default"):
            return {"id": device.get("id"), "name": device.get("name")}
    return None


def run_refresh_devices_action() -> dict[str, object]:
    devices = run_list_devices()
    default_device = _extract_default_device(devices)

    if devices:
        status_message = f"Loaded {len(devices)} Spotify devices."
    else:
        status_message = "Spotify returned no available devices."

    if default_device and default_device.get("id"):
        status_message = (
            f"{status_message} Default: {default_device.get('name') or '(unnamed)'} "
            f"[{default_device.get('id')}]"
        )

    return {
        "ok": True,
        "action": "refresh",
        "devices": devices,
        "default_device": default_device,
        "status_message": status_message,
    }


def run_set_default_device_action(device_id: str) -> dict[str, object]:
    selected = run_set_default_device(device_id)
    devices = run_list_devices()
    default_device = _extract_default_device(devices) or selected

    return {
        "ok": True,
        "action": "set_default",
        "devices": devices,
        "default_device": default_device,
        "status_message": (
            f"Default device set: {selected.get('name') or '(unnamed)'} "
            f"[{selected.get('id')}]"
        ),
    }


def run_auto_set_default_device_action() -> dict[str, object]:
    selected = run_auto_set_default_device()
    devices = run_list_devices()
    default_device = _extract_default_device(devices) or selected

    return {
        "ok": True,
        "action": "auto_set_default",
        "devices": devices,
        "default_device": default_device,
        "status_message": (
            f"Auto-selected default device: {selected.get('name') or '(unnamed)'} "
            f"[{selected.get('id')}]"
        ),
    }
