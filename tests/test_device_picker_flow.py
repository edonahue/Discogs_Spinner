from __future__ import annotations

from discogs_player.use_cases import device_picker_flow


def _devices() -> list[dict[str, object]]:
    return [
        {
            "id": "dev-1",
            "name": "Desk",
            "type": "Computer",
            "is_active": True,
            "is_restricted": False,
            "is_default": True,
        },
        {
            "id": "dev-2",
            "name": "Phone",
            "type": "Smartphone",
            "is_active": False,
            "is_restricted": False,
            "is_default": False,
        },
    ]


def test_refresh_devices_action(monkeypatch):
    monkeypatch.setattr(device_picker_flow, "run_list_devices", _devices)

    payload = device_picker_flow.run_refresh_devices_action()

    assert payload["action"] == "refresh"
    assert len(payload["devices"]) == 2
    assert payload["default_device"] == {"id": "dev-1", "name": "Desk"}
    assert "Loaded 2 Spotify devices." in str(payload["status_message"])


def test_set_default_device_action(monkeypatch):
    called: list[str] = []

    def _set_default(device_id: str):
        called.append(device_id)
        return {"id": device_id, "name": "Phone"}

    monkeypatch.setattr(device_picker_flow, "run_set_default_device", _set_default)
    monkeypatch.setattr(
        device_picker_flow,
        "run_list_devices",
        lambda: [
            {
                "id": "dev-1",
                "name": "Desk",
                "type": "Computer",
                "is_active": True,
                "is_restricted": False,
                "is_default": False,
            },
            {
                "id": "dev-2",
                "name": "Phone",
                "type": "Smartphone",
                "is_active": False,
                "is_restricted": False,
                "is_default": True,
            },
        ],
    )

    payload = device_picker_flow.run_set_default_device_action("dev-2")

    assert called == ["dev-2"]
    assert payload["action"] == "set_default"
    assert payload["default_device"] == {"id": "dev-2", "name": "Phone"}
    assert "Default device set: Phone [dev-2]" == payload["status_message"]


def test_auto_set_default_device_action(monkeypatch):
    monkeypatch.setattr(
        device_picker_flow,
        "run_auto_set_default_device",
        lambda: {"id": "dev-1", "name": "Desk"},
    )
    monkeypatch.setattr(device_picker_flow, "run_list_devices", _devices)

    payload = device_picker_flow.run_auto_set_default_device_action()

    assert payload["action"] == "auto_set_default"
    assert payload["default_device"] == {"id": "dev-1", "name": "Desk"}
    assert "Auto-selected default device: Desk [dev-1]" == payload["status_message"]
