"""Device picker controls for Spotify playback target selection."""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

_SPOTIFY_DASHBOARD_URL = "https://developer.spotify.com/dashboard"
_SPOTIFY_OAUTH_GUIDE_URL = (
    "https://developer.spotify.com/documentation/web-api/tutorials/code-flow"
)


class DevicePicker(Gtk.Box):
    def __init__(
        self,
        *,
        on_refresh: Callable[[], None] | None = None,
        on_set_default: Callable[[], None] | None = None,
        on_auto_select: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_margin_top(8)
        self.set_margin_bottom(8)
        self.set_margin_start(8)
        self.set_margin_end(8)

        self._device_ids: list[str] = []
        self._devices_model = Gtk.StringList.new([])
        self._actions_enabled = True

        heading = Gtk.Label(label="Spotify Devices")
        heading.set_xalign(0.0)
        heading.add_css_class("title-4")
        self.append(heading)
        self._heading = heading

        self._capability_hint_label = Gtk.Label(label="")
        self._capability_hint_label.set_xalign(0.0)
        self._capability_hint_label.set_wrap(True)
        self._capability_hint_label.add_css_class("dim-label")
        self._capability_hint_label.set_visible(False)
        self.append(self._capability_hint_label)

        self._help_links_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._spotify_dashboard_link = Gtk.LinkButton.new(_SPOTIFY_DASHBOARD_URL)
        self._spotify_dashboard_link.set_label("Spotify Dashboard")
        self._spotify_dashboard_link.set_halign(Gtk.Align.START)
        self._help_links_row.append(self._spotify_dashboard_link)

        self._spotify_oauth_guide_link = Gtk.LinkButton.new(_SPOTIFY_OAUTH_GUIDE_URL)
        self._spotify_oauth_guide_link.set_label("Spotify OAuth Guide")
        self._spotify_oauth_guide_link.set_halign(Gtk.Align.START)
        self._help_links_row.append(self._spotify_oauth_guide_link)
        self._help_links_row.set_visible(False)
        self.append(self._help_links_row)

        self._default_label = Gtk.Label(label="Default: none")
        self._default_label.set_xalign(0.0)
        self._default_label.set_wrap(True)
        self.append(self._default_label)

        self._drop_down = Gtk.DropDown.new(self._devices_model, None)
        self._drop_down.set_hexpand(True)
        self.append(self._drop_down)

        button_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._refresh_button = Gtk.Button(label="Refresh Devices")
        if on_refresh is not None:
            self._refresh_button.connect("clicked", lambda *_: on_refresh())
        button_row.append(self._refresh_button)

        self._set_default_button = Gtk.Button(label="Set Default")
        if on_set_default is not None:
            self._set_default_button.connect("clicked", lambda *_: on_set_default())
        button_row.append(self._set_default_button)

        self._auto_button = Gtk.Button(label="Auto Select")
        if on_auto_select is not None:
            self._auto_button.connect("clicked", lambda *_: on_auto_select())
        button_row.append(self._auto_button)
        self.append(button_row)

        self._result_label = Gtk.Label(label="Status: idle")
        self._result_label.set_xalign(0.0)
        self._result_label.set_wrap(True)
        self.append(self._result_label)

        self.set_devices([])

    def _clear_model(self) -> None:
        while self._devices_model.get_n_items() > 0:
            self._devices_model.remove(self._devices_model.get_n_items() - 1)

    @staticmethod
    def _device_label(device: dict[str, object]) -> str:
        name = str(device.get("name") or "Unknown")
        device_type = str(device.get("type") or "Unknown")
        device_id = str(device.get("id") or "")
        flags: list[str] = []
        if device.get("is_default"):
            flags.append("default")
        if device.get("is_active"):
            flags.append("active")
        if device.get("is_restricted"):
            flags.append("restricted")

        suffix = f" ({', '.join(flags)})" if flags else ""
        return f"{name} [{device_type}] {device_id}{suffix}"

    def set_default_device(self, device: dict[str, object] | None) -> None:
        if not isinstance(device, dict):
            self._default_label.set_text("Default: none")
            return
        device_id = str(device.get("id") or "").strip()
        device_name = str(device.get("name") or "").strip()
        if device_id:
            self._default_label.set_text(
                f"Default: {device_name or '(unnamed)'} [{device_id}]"
            )
        else:
            self._default_label.set_text("Default: none")

    def _apply_control_sensitivity(self) -> None:
        has_devices = bool(self._device_ids)
        controls_enabled = bool(self._actions_enabled)
        self._refresh_button.set_sensitive(controls_enabled)
        self._auto_button.set_sensitive(controls_enabled)
        self._drop_down.set_sensitive(controls_enabled and has_devices)
        self._set_default_button.set_sensitive(controls_enabled and has_devices)

    def set_capability_hint(self, message: str | None, *, show_controls: bool) -> None:
        hint = str(message or "").strip()
        self._capability_hint_label.set_text(hint)
        self._capability_hint_label.set_visible(bool(hint))
        self._help_links_row.set_visible(bool(hint) and (not show_controls))
        if hint:
            self._heading.set_label("Playback Devices")
        else:
            self._heading.set_label("Spotify Devices")
        if show_controls:
            self._actions_enabled = True
            self._apply_control_sensitivity()
            return

        if not show_controls:
            self._device_ids = []
            self._clear_model()
            self.set_default_device(None)
            self._actions_enabled = False
            self._apply_control_sensitivity()

    def set_actions_enabled(self, enabled: bool) -> None:
        self._actions_enabled = bool(enabled)
        self._apply_control_sensitivity()

    def set_devices(self, devices: list[dict[str, object]]) -> None:
        self._device_ids = []
        self._clear_model()

        default_index = -1
        row_index = 0
        for device in devices:
            device_id = str(device.get("id") or "").strip()
            if not device_id:
                continue
            self._device_ids.append(device_id)
            self._devices_model.append(self._device_label(device))
            if device.get("is_default"):
                default_index = row_index if default_index < 0 else default_index
            row_index += 1

        if self._device_ids:
            if default_index >= 0 and default_index < len(self._device_ids):
                self._drop_down.set_selected(default_index)
            else:
                self._drop_down.set_selected(0)
        self._apply_control_sensitivity()

        default_device = None
        for device in devices:
            if device.get("is_default"):
                default_device = device
                break
        self.set_default_device(default_device)

    def selected_device_id(self) -> str | None:
        selected = int(self._drop_down.get_selected())
        if selected < 0 or selected >= len(self._device_ids):
            return None
        return self._device_ids[selected]

    def set_result(self, message: str) -> None:
        self._result_label.set_text(message.strip() or "Status: idle")

    def set_error(self, message: str) -> None:
        self._result_label.set_text(f"Error: {message.strip() or 'unknown error'}")
