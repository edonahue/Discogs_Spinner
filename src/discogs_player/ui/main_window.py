"""Main GTK window for Discogs Player."""

from __future__ import annotations

import json
import traceback

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gtk

from discogs_player.services.matching import MatchingDependencyError
from discogs_player.services.spotify_client import SpotifyApiError, SpotifyPlaybackError
from discogs_player.services.spotify_oauth import SpotifyAuthError, SpotifyDependencyError
from discogs_player.use_cases.browse_release_grid import run_browse_release_grid
from discogs_player.use_cases.device_management import NoSpotifyDevicesError
from discogs_player.use_cases.device_picker_flow import (
    run_auto_set_default_device_action,
    run_refresh_devices_action,
    run_set_default_device_action,
)
from discogs_player.use_cases.match_play_flow import (
    run_match_action,
    run_override_action,
    run_play_action,
)
from discogs_player.use_cases.play_release import MissingLastSpinError
from discogs_player.use_cases.spin_flow import run_play_last_spin_action, run_spin_action
from discogs_player.use_cases.value_examples import run_market_value_examples
from discogs_player.ui.sorting import sort_release_items
from discogs_player.ui.widgets.album_detail import AlbumDetail
from discogs_player.ui.widgets.cover_carousel import CoverCarousel
from discogs_player.ui.widgets.device_picker import DevicePicker
from discogs_player.ui.widgets.filters import FilterBar
from discogs_player.ui.widgets.spin_wheel import SpinWheel
from discogs_player.ui.widgets.text_menu import ReleaseTextMenu

_IPOD_NANO_CSS = """
window.ipod-shell {
  background-image: linear-gradient(180deg, #0f1115 0%, #07080a 45%, #030405 100%);
}

.ipod-root {
  background-image: radial-gradient(circle at top, #171b22 0%, #0a0d12 50%, #050607 100%);
}

.ipod-mode-row {
  padding: 6px 8px;
}

.ipod-mode-title {
  color: #d3d7df;
  font-weight: 700;
}

.ipod-mode-toggle {
  border-radius: 18px;
  padding: 5px 12px;
}

.ipod-panel {
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background-color: rgba(8, 11, 16, 0.84);
  padding: 8px;
}

.ipod-panel label {
  color: #d8dee9;
}

.ipod-panel .title-4 {
  color: #eef2f8;
}

.ipod-filter-bar {
  border-radius: 12px;
}

.ipod-status {
  color: #b9c4d6;
}

.ipod-text-menu,
.ipod-carousel {
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background-color: rgba(8, 11, 16, 0.92);
}

.ipod-menu-row {
  border-radius: 10px;
}

.ipod-menu-primary {
  color: #f2f4f8;
  font-weight: 600;
}

.ipod-menu-secondary,
.ipod-menu-chevron,
.ipod-carousel-meta {
  color: #93a1b8;
}

.ipod-carousel-title {
  color: #e9edf5;
  font-weight: 700;
}

.ipod-cover-frame {
  margin: 10px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background-color: rgba(4, 6, 9, 0.95);
}

.ipod-cover-placeholder {
  color: #7f8ba0;
  font-size: 22px;
}
"""


class MainWindow(Adw.ApplicationWindow):
    def __init__(
        self,
        app: Adw.Application,
        *,
        limit: int = 50,
        preload_covers: bool = True,
    ) -> None:
        super().__init__(application=app, title="Discogs Player")
        self.add_css_class("ipod-shell")
        self.set_default_size(1200, 820)
        self._install_css()

        self._limit = max(1, int(limit))
        self._preload_covers = bool(preload_covers)
        self._selected_release_id: int | None = None
        self._selected_release: dict[str, object] | None = None
        self._visible_release_ids: list[int] = []
        self._syncing_selection = False
        self._syncing_mode_toggle = False
        self._scroll_accum = 0.0

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.add_css_class("ipod-root")
        self.set_content(root)

        self._filters = FilterBar(default_limit=self._limit, on_refresh=self.refresh)
        self._filters.add_css_class("ipod-panel")
        self._filters.add_css_class("ipod-filter-bar")
        self._filters_scroll = Gtk.ScrolledWindow()
        self._filters_scroll.set_hexpand(True)
        self._filters_scroll.set_vexpand(False)
        self._filters_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        self._filters_scroll.set_child(self._filters)
        root.append(self._filters_scroll)

        content = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)
        content.set_resize_start_child(True)
        content.set_shrink_start_child(True)
        content.set_resize_end_child(True)
        content.set_shrink_end_child(True)
        content.set_wide_handle(True)
        root.append(content)

        browser_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        browser_panel.set_margin_top(8)
        browser_panel.set_margin_bottom(8)
        browser_panel.set_margin_start(8)
        browser_panel.set_margin_end(8)
        self._browse_panel = browser_panel
        content.set_start_child(browser_panel)

        mode_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        mode_row.add_css_class("ipod-mode-row")
        browser_panel.append(mode_row)

        mode_title = Gtk.Label(label="Browse Mode")
        mode_title.set_xalign(0.0)
        mode_title.add_css_class("ipod-mode-title")
        mode_row.append(mode_title)

        self._text_mode = Gtk.ToggleButton(label="Text Menu")
        self._text_mode.add_css_class("ipod-mode-toggle")
        self._text_mode.connect("toggled", self._handle_text_mode_toggled)
        mode_row.append(self._text_mode)

        self._carousel_mode = Gtk.ToggleButton(label="Carousel")
        self._carousel_mode.add_css_class("ipod-mode-toggle")
        self._carousel_mode.connect("toggled", self._handle_carousel_mode_toggled)
        mode_row.append(self._carousel_mode)

        self._browse_stack = Gtk.Stack()
        self._browse_stack.set_hexpand(True)
        self._browse_stack.set_vexpand(True)
        self._browse_stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        browser_panel.append(self._browse_stack)
        scroll_controller = Gtk.EventControllerScroll.new(
            Gtk.EventControllerScrollFlags.VERTICAL
            | Gtk.EventControllerScrollFlags.HORIZONTAL
            | Gtk.EventControllerScrollFlags.DISCRETE
        )
        scroll_controller.connect("scroll", self._handle_browse_scroll)
        self._browse_stack.add_controller(scroll_controller)

        self._text_menu = ReleaseTextMenu(on_selection_changed=self._handle_release_selected)
        self._carousel = CoverCarousel(on_selection_changed=self._handle_release_selected)
        self._browse_stack.add_named(self._text_menu, "text")
        self._browse_stack.add_named(self._carousel, "carousel")

        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        sidebar.set_valign(Gtk.Align.START)
        sidebar.set_margin_top(8)
        sidebar.set_margin_bottom(8)
        sidebar.set_margin_start(8)
        sidebar.set_margin_end(8)
        self._sidebar_scroll = Gtk.ScrolledWindow()
        self._sidebar_scroll.set_hexpand(False)
        self._sidebar_scroll.set_vexpand(True)
        self._sidebar_scroll.set_min_content_width(360)
        self._sidebar_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self._sidebar_scroll.set_child(sidebar)
        content.set_end_child(self._sidebar_scroll)

        self._album_detail = AlbumDetail(
            on_auto_match=self._handle_auto_match_clicked,
            on_override=self._handle_override_clicked,
            on_play=self._handle_play_clicked,
        )
        self._album_detail.add_css_class("ipod-panel")
        sidebar.append(self._album_detail)
        self._spin_wheel = SpinWheel(
            on_spin=self._handle_spin_clicked,
            on_play_last_spin=self._handle_play_last_spin_clicked,
        )
        self._spin_wheel.add_css_class("ipod-panel")
        sidebar.append(self._spin_wheel)
        self._device_picker = DevicePicker(
            on_refresh=self._handle_devices_refresh_clicked,
            on_set_default=self._handle_set_default_device_clicked,
            on_auto_select=self._handle_auto_select_device_clicked,
        )
        self._device_picker.add_css_class("ipod-panel")
        sidebar.append(self._device_picker)
        value_heading = Gtk.Label(label="Collection Value Examples")
        value_heading.set_xalign(0.0)
        value_heading.add_css_class("title-5")
        sidebar.append(value_heading)

        self._value_examples = Gtk.Label(label="No priced releases with median values yet.")
        self._value_examples.set_xalign(0.0)
        self._value_examples.set_wrap(True)
        self._value_examples.add_css_class("dim-label")
        sidebar.append(self._value_examples)

        self._status = Gtk.Label(label="Ready")
        self._status.add_css_class("ipod-status")
        self._status.set_xalign(0.0)
        self._status.set_margin_top(6)
        self._status.set_margin_bottom(8)
        self._status.set_margin_start(12)
        self._status.set_margin_end(12)
        root.append(self._status)

        self._text_mode.set_active(True)
        self._set_browse_mode("text")

        key_controller = Gtk.EventControllerKey.new()
        key_controller.connect("key-pressed", self._handle_key_pressed)
        self.add_controller(key_controller)

    def refresh(self) -> dict[str, object]:
        filters = self._current_filters()
        try:
            return self.load_releases_with_filters(
                q=filters["q"],  # type: ignore[arg-type]
                year=filters["year"],  # type: ignore[arg-type]
                genres=filters["genres"],  # type: ignore[arg-type]
                styles=filters["styles"],  # type: ignore[arg-type]
                unmatched=bool(filters["unmatched"]),
                sort_mode=str(filters.get("sort") or "artist_title"),
                limit=int(filters["limit"]),
            )
        except Exception as exc:
            message = self._friendly_error_message(exc)
            self._set_status(message)
            return {
                "ok": False,
                "error": message,
                "query": filters.get("q"),
                "year": filters.get("year"),
                "genres": filters.get("genres"),
                "styles": filters.get("styles"),
                "unmatched": bool(filters.get("unmatched")),
                "sort": str(filters.get("sort") or "artist_title"),
                "limit": int(filters.get("limit") or self._limit),
            }

    def _current_filters(self) -> dict[str, object]:
        return self._filters.current_filters()

    def _install_css(self) -> None:
        display = self.get_display()
        if display is None:
            return
        provider = Gtk.CssProvider()
        provider.load_from_data(_IPOD_NANO_CSS.encode("utf-8"))
        Gtk.StyleContext.add_provider_for_display(
            display,
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _set_browse_mode(self, mode: str) -> None:
        self._syncing_mode_toggle = True
        try:
            if mode == "text":
                self._text_mode.set_active(True)
                self._carousel_mode.set_active(False)
                self._browse_stack.set_visible_child_name("text")
                return
            if mode == "carousel":
                self._carousel_mode.set_active(True)
                self._text_mode.set_active(False)
                self._browse_stack.set_visible_child_name("carousel")
        finally:
            self._syncing_mode_toggle = False

    def _handle_text_mode_toggled(self, button: Gtk.ToggleButton) -> None:
        if self._syncing_mode_toggle:
            return
        if not button.get_active():
            if not self._carousel_mode.get_active():
                self._set_browse_mode("text")
            return
        self._set_browse_mode("text")

    def _handle_carousel_mode_toggled(self, button: Gtk.ToggleButton) -> None:
        if self._syncing_mode_toggle:
            return
        if not button.get_active():
            if not self._text_mode.get_active():
                self._set_browse_mode("carousel")
            return
        self._set_browse_mode("carousel")

    def _set_status(self, message: str) -> None:
        self._status.set_text(message)

    def _active_browse_mode(self) -> str:
        visible = self._browse_stack.get_visible_child_name()
        return str(visible or "text")

    def _toggle_browse_mode(self) -> None:
        if self._active_browse_mode() == "text":
            self._set_browse_mode("carousel")
            self._set_status("Browse mode: Carousel")
        else:
            self._set_browse_mode("text")
            self._set_status("Browse mode: Text Menu")

    def _navigate_selection(self, delta: int) -> None:
        if not self._visible_release_ids:
            return

        if self._selected_release_id in self._visible_release_ids:
            current_index = self._visible_release_ids.index(int(self._selected_release_id))
        else:
            current_index = 0
        next_index = (current_index + int(delta)) % len(self._visible_release_ids)
        target_release_id = self._visible_release_ids[next_index]
        self._focus_release_id(target_release_id, allow_expand_limit=False)

    def _focused_widget_is_text_input(self) -> bool:
        focus = self.get_focus()
        return isinstance(focus, (Gtk.Entry, Gtk.SpinButton, Gtk.TextView, Gtk.DropDown))

    @staticmethod
    def _is_descendant_of(widget: Gtk.Widget | None, ancestor: Gtk.Widget | None) -> bool:
        if widget is None or ancestor is None:
            return False
        current: Gtk.Widget | None = widget
        while current is not None:
            if current is ancestor:
                return True
            current = current.get_parent()
        return False

    def _handle_key_pressed(
        self,
        _controller: Gtk.EventControllerKey,
        keyval: int,
        _keycode: int,
        _state: Gdk.ModifierType,
    ) -> bool:
        focus = self.get_focus()
        if focus is not None and not self._is_descendant_of(focus, self._browse_panel):
            return False
        if self._focused_widget_is_text_input():
            return False

        if keyval in (Gdk.KEY_Up, Gdk.KEY_KP_Up, Gdk.KEY_Left, Gdk.KEY_KP_Left):
            self._navigate_selection(-1)
            return True
        if keyval in (Gdk.KEY_Down, Gdk.KEY_KP_Down, Gdk.KEY_Right, Gdk.KEY_KP_Right):
            self._navigate_selection(1)
            return True
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            self._toggle_browse_mode()
            return True
        return False

    def _handle_browse_scroll(
        self,
        _controller: Gtk.EventControllerScroll,
        dx: float,
        dy: float,
    ) -> bool:
        # Wheel/trackpad movement is thresholded to one step per logical notch.
        axis_delta = dy if abs(dy) >= abs(dx) else dx
        if axis_delta == 0:
            return False

        self._scroll_accum += float(axis_delta)
        moved = False
        while self._scroll_accum >= 1.0:
            self._navigate_selection(1)
            self._scroll_accum -= 1.0
            moved = True
        while self._scroll_accum <= -1.0:
            self._navigate_selection(-1)
            self._scroll_accum += 1.0
            moved = True
        return moved

    def _sync_release_selection(self, discogs_release_id: int) -> None:
        if self._syncing_selection:
            return
        self._syncing_selection = True
        try:
            self._text_menu.select_release(discogs_release_id)
            self._carousel.select_release(discogs_release_id)
        finally:
            self._syncing_selection = False

    def _format_value_example(self, item: dict[str, object]) -> str:
        artist = str(item.get("artist") or "").strip() or "Unknown Artist"
        title = str(item.get("title") or "").strip() or "Unknown Title"
        median = item.get("market_median")
        median_text = f"{float(median):.2f}" if isinstance(median, (int, float)) else "n/a"
        currency = str(item.get("market_currency") or "").strip()
        if currency:
            return f"{artist} - {title} ({median_text} {currency})"
        return f"{artist} - {title} ({median_text})"

    def _refresh_value_examples(self) -> None:
        try:
            report = run_market_value_examples(limit=2)
        except Exception as exc:
            message = self._friendly_error_message(exc)
            self._value_examples.set_text(f"Value examples unavailable: {message}")
            return

        high = report.get("high_priced")
        low = report.get("low_priced")
        high_rows = high if isinstance(high, list) else []
        low_rows = low if isinstance(low, list) else []
        if not high_rows and not low_rows:
            self._value_examples.set_text("No priced releases with median values yet.")
            return

        high_text = ", ".join(
            self._format_value_example(item)
            for item in high_rows
            if isinstance(item, dict)
        )
        low_text = ", ".join(
            self._format_value_example(item)
            for item in low_rows
            if isinstance(item, dict)
        )
        self._value_examples.set_text(
            f"High: {high_text or '(none)'}\nLow: {low_text or '(none)'}"
        )

    def _selected_release_id_or_raise(self) -> int:
        if self._selected_release_id is None:
            raise ValueError("Select a release first.")
        return self._selected_release_id

    def _friendly_error_message(self, exc: Exception) -> str:
        if isinstance(
            exc,
            (
                SpotifyDependencyError,
                SpotifyAuthError,
                SpotifyApiError,
                SpotifyPlaybackError,
                MatchingDependencyError,
                NoSpotifyDevicesError,
                MissingLastSpinError,
                ValueError,
            ),
        ):
            return str(exc)
        return f"{type(exc).__name__}: {exc}"

    def _focus_release_id(self, discogs_release_id: int, *, allow_expand_limit: bool = True) -> bool:
        selected = False
        if self._text_menu.select_release(discogs_release_id):
            selected = True
        if self._carousel.select_release(discogs_release_id):
            selected = True
        if selected:
            return True

        if not allow_expand_limit:
            return False

        filters = self._current_filters()
        expanded_limit = max(int(filters.get("limit") or self._limit), 250)
        self.load_releases_with_filters(
            q=filters.get("q"),  # type: ignore[arg-type]
            year=filters.get("year"),  # type: ignore[arg-type]
            genres=filters.get("genres"),  # type: ignore[arg-type]
            styles=filters.get("styles"),  # type: ignore[arg-type]
            unmatched=bool(filters.get("unmatched")),
            sort_mode=str(filters.get("sort") or "artist_title"),
            limit=expanded_limit,
        )
        selected = False
        if self._text_menu.select_release(discogs_release_id):
            selected = True
        if self._carousel.select_release(discogs_release_id):
            selected = True
        return selected

    def _handle_release_selected(self, item: dict[str, object] | None) -> None:
        self._selected_release = dict(item) if isinstance(item, dict) else None

        if isinstance(item, dict) and isinstance(item.get("discogs_release_id"), int):
            self._selected_release_id = int(item["discogs_release_id"])
            self._album_detail.set_release(item)
            artist = str(item.get("artist") or "Unknown Artist")
            title = str(item.get("title") or "Unknown Title")
            self._set_status(f"Selected release {self._selected_release_id}: {artist} - {title}")
            self._sync_release_selection(self._selected_release_id)
            return

        self._selected_release_id = None
        self._album_detail.set_release(None)
        self._set_status("No release selected.")

    def _handle_auto_match_clicked(self) -> None:
        try:
            release_id = self._selected_release_id_or_raise()
            payload = run_match_action(release_id)
            self._album_detail.set_match_result(payload)
            self._set_status(str(payload.get("status_message") or "Auto-match completed."))
            if self._selected_release is not None:
                self._selected_release["spotify_album_id"] = payload.get("spotify_album_id")
        except Exception as exc:
            message = self._friendly_error_message(exc)
            self._album_detail.set_error(message)
            self._set_status(message)

    def _handle_override_clicked(self) -> None:
        try:
            release_id = self._selected_release_id_or_raise()
            spotify_album_id = self._album_detail.get_override_album_id()
            payload = run_override_action(release_id, spotify_album_id)
            self._album_detail.set_override_result(payload)
            self._set_status(str(payload.get("status_message") or "Override saved."))
            if self._selected_release is not None:
                self._selected_release["spotify_album_id"] = payload.get("spotify_album_id")
        except Exception as exc:
            message = self._friendly_error_message(exc)
            self._album_detail.set_error(message)
            self._set_status(message)

    def _handle_play_clicked(self) -> None:
        try:
            release_id = self._selected_release_id_or_raise()
            payload = run_play_action(release_id)
            self._album_detail.set_play_result(payload)
            self._set_status(str(payload.get("status_message") or "Play action completed."))
            if self._selected_release is not None:
                album_id = payload.get("spotify_album_id")
                if album_id:
                    self._selected_release["spotify_album_id"] = album_id
        except Exception as exc:
            message = self._friendly_error_message(exc)
            self._album_detail.set_error(message)
            self._set_status(message)

    def _handle_devices_refresh_clicked(self) -> None:
        try:
            payload = run_refresh_devices_action()
            self._device_picker.set_devices(payload["devices"])  # type: ignore[arg-type]
            self._device_picker.set_default_device(payload.get("default_device"))  # type: ignore[arg-type]
            message = str(payload.get("status_message") or "Device list refreshed.")
            self._device_picker.set_result(message)
            self._set_status(message)
        except Exception as exc:
            message = self._friendly_error_message(exc)
            self._device_picker.set_error(message)
            self._set_status(message)

    def _handle_set_default_device_clicked(self) -> None:
        try:
            selected_device_id = self._device_picker.selected_device_id()
            if not selected_device_id:
                raise ValueError("Select a device first.")

            payload = run_set_default_device_action(selected_device_id)
            self._device_picker.set_devices(payload["devices"])  # type: ignore[arg-type]
            self._device_picker.set_default_device(payload.get("default_device"))  # type: ignore[arg-type]
            message = str(payload.get("status_message") or "Default device updated.")
            self._device_picker.set_result(message)
            self._set_status(message)
        except Exception as exc:
            message = self._friendly_error_message(exc)
            self._device_picker.set_error(message)
            self._set_status(message)

    def _handle_auto_select_device_clicked(self) -> None:
        try:
            payload = run_auto_set_default_device_action()
            self._device_picker.set_devices(payload["devices"])  # type: ignore[arg-type]
            self._device_picker.set_default_device(payload.get("default_device"))  # type: ignore[arg-type]
            message = str(payload.get("status_message") or "Auto-selected default device.")
            self._device_picker.set_result(message)
            self._set_status(message)
        except Exception as exc:
            message = self._friendly_error_message(exc)
            self._device_picker.set_error(message)
            self._set_status(message)

    def _handle_spin_clicked(self) -> None:
        try:
            filters = self._current_filters()
            seed = self._spin_wheel.get_seed()
            self._set_status("Spinning...")
            payload = run_spin_action(
                q=filters["q"],  # type: ignore[arg-type]
                year=filters["year"],  # type: ignore[arg-type]
                genres=filters["genres"],  # type: ignore[arg-type]
                styles=filters["styles"],  # type: ignore[arg-type]
                unmatched=bool(filters["unmatched"]),
                seed=seed,
            )
            self._spin_wheel.animate_spin_result(payload, on_complete=self._apply_spin_result)
        except Exception as exc:
            message = self._friendly_error_message(exc)
            self._spin_wheel.set_error(message)
            self._set_status(message)

    def _apply_spin_result(self, payload: dict[str, object]) -> None:
        release = payload.get("release")
        if isinstance(release, dict):
            release_id = release.get("discogs_release_id")
            if isinstance(release_id, int):
                focused = self._focus_release_id(release_id)
                if not focused:
                    self._selected_release_id = release_id
                    self._selected_release = dict(release)
                    self._album_detail.set_release(release)

        self._set_status(str(payload.get("status_message") or "Spin complete."))

    def _handle_play_last_spin_clicked(self) -> None:
        try:
            payload = run_play_last_spin_action()
            self._spin_wheel.set_play_result(payload)
            message = str(payload.get("status_message") or "Play last spin complete.")

            raw = payload.get("raw")
            if isinstance(raw, dict):
                release_id = raw.get("discogs_release_id")
                if isinstance(release_id, int):
                    self._focus_release_id(release_id)

            self._set_status(message)
        except Exception as exc:
            message = self._friendly_error_message(exc)
            self._spin_wheel.set_error(message)
            self._set_status(message)

    def load_releases(self, *, q: str | None = None) -> dict[str, object]:
        return self.load_releases_with_filters(q=q)

    def load_releases_with_filters(
        self,
        *,
        q: str | None = None,
        year: str | None = None,
        genres: list[str] | None = None,
        styles: list[str] | None = None,
        unmatched: bool = False,
        sort_mode: str = "artist_title",
        limit: int | None = None,
    ) -> dict[str, object]:
        self._status.set_text("Loading releases...")
        effective_limit = max(1, int(limit if limit is not None else self._limit))
        items_raw = run_browse_release_grid(
            limit=effective_limit,
            q=q,
            year=year,
            genres=genres or [],
            styles=styles or [],
            unmatched=unmatched,
            preload_covers=self._preload_covers,
        )
        items = sort_release_items(items_raw, sort_mode=sort_mode)
        self._visible_release_ids = [
            int(item["discogs_release_id"])
            for item in items
            if isinstance(item.get("discogs_release_id"), int)
        ]
        self._refresh_value_examples()

        self._syncing_selection = True
        try:
            self._text_menu.set_items(items)
            self._carousel.set_items(items)
        finally:
            self._syncing_selection = False

        if items:
            self._handle_release_selected(items[0])
        else:
            self._visible_release_ids = []
            self._handle_release_selected(None)

        cover_count = sum(1 for item in items if item.get("cover_path"))
        if not items:
            self._album_detail.set_release(None)
            self._set_status("Loaded 0 releases.")
        else:
            self._set_status(
                f"Loaded {len(items)} releases ({cover_count} covers cached)."
            )
        return {
            "ok": True,
            "item_count": len(items),
            "cover_cached_count": cover_count,
            "query": q,
            "year": year,
            "genres": genres or [],
            "styles": styles or [],
            "unmatched": unmatched,
            "sort": sort_mode,
            "limit": effective_limit,
        }


class DiscogsPlayerApp(Adw.Application):
    def __init__(self, *, limit: int = 50, preload_covers: bool = True, smoke_test: bool = False):
        super().__init__(application_id="com.discogs_player.app")
        self._limit = max(1, int(limit))
        self._preload_covers = bool(preload_covers)
        self._smoke_test = bool(smoke_test)
        self.exit_code = 0
        self._did_activate = False

    def do_activate(self) -> None:  # pragma: no cover - driven by integration runtime
        if self._did_activate:
            return
        self._did_activate = True

        window = MainWindow(self, limit=self._limit, preload_covers=self._preload_covers)
        window.present()

        try:
            report = window.load_releases()
        except Exception as exc:
            self.exit_code = 1
            report = {
                "ok": False,
                "error": str(exc),
                "traceback": traceback.format_exc(limit=4),
            }

        if self._smoke_test:
            print(json.dumps(report, sort_keys=True))
            self.quit()
