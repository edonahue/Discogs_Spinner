"""Spin controls for selecting and replaying releases."""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk

from discogs_player.ui.utils.formatting import format_market_summary


class SpinWheel(Gtk.Box):
    _SPIN_FRAMES = ("|", "/", "-", "\\")
    _SPIN_INTERVAL_MS = 80
    _SPIN_TICKS = 28
    _TEXT_UPDATE_EVERY = 3
    _SPIN_MESSAGES = (
        "Status: shuffling the stack",
        "Status: narrowing picks",
        "Status: locking selection",
    )

    def __init__(
        self,
        *,
        on_spin: Callable[[], None] | None = None,
        on_play_last_spin: Callable[[], None] | None = None,
        compact: bool = False,
    ) -> None:
        super().__init__(
            orientation=Gtk.Orientation.HORIZONTAL
            if compact
            else Gtk.Orientation.VERTICAL,
            spacing=6,
        )
        self._compact = bool(compact)
        if not self._compact:
            self.set_margin_top(8)
            self.set_margin_bottom(8)
            self.set_margin_start(8)
            self.set_margin_end(8)
        else:
            self.set_halign(Gtk.Align.END)
            self.set_valign(Gtk.Align.CENTER)

        heading = Gtk.Label(label="Spin")
        heading.set_xalign(0.0)
        heading.add_css_class("title-4")
        if not self._compact:
            self.append(heading)

        seed_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        seed_label = Gtk.Label(label="Seed")
        seed_label.set_xalign(0.0)
        seed_row.append(seed_label)

        self._seed_entry = Gtk.Entry()
        self._seed_entry.set_width_chars(12)
        self._seed_entry.set_placeholder_text("optional int")
        seed_row.append(self._seed_entry)
        if not self._compact:
            self.append(seed_row)

        button_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        if self._compact:
            button_row.set_halign(Gtk.Align.END)
            button_row.set_hexpand(True)
        self._button_row = button_row
        self._spin_button = Gtk.Button(label="Spin")
        if on_spin is not None:
            self._spin_button.connect("clicked", lambda *_: on_spin())
        button_row.append(self._spin_button)

        self._play_last_button = Gtk.Button(label="Play Last Spin")
        if on_play_last_spin is not None:
            self._play_last_button.connect("clicked", lambda *_: on_play_last_spin())
        button_row.append(self._play_last_button)
        self.append(button_row)

        self._selected_label = Gtk.Label(label="Selected: (none)")
        self._selected_label.set_xalign(0.0)
        self._selected_label.set_wrap(True)
        if not self._compact:
            self.append(self._selected_label)

        self._selected_market_label = Gtk.Label(label="Selected Market: n/a")
        self._selected_market_label.set_xalign(0.0)
        self._selected_market_label.set_wrap(True)
        self._selected_market_label.add_css_class("dim-label")
        if not self._compact:
            self.append(self._selected_market_label)

        self._result_label = Gtk.Label(label="Status: idle")
        self._result_label.set_xalign(0.0)
        self._result_label.set_wrap(True)
        if not self._compact:
            self.append(self._result_label)

        self._spin_source_id: int | None = None
        self._spin_tick = 0
        self._spin_payload: dict[str, object] | None = None
        self._spin_complete_callback: Callable[[dict[str, object]], None] | None = None

    def set_spotify_capability(self, *, playback_available: bool) -> None:
        if playback_available:
            self._play_last_button.set_label("Play Last Spin")
        else:
            self._play_last_button.set_label("Open Last Spin in Spotify")

    def set_context_release(self, item: dict[str, object] | None) -> None:
        if not isinstance(item, dict):
            self._selected_market_label.set_text("Selected Market: n/a")
            return
        self._selected_market_label.set_text(format_market_summary(item))

    def get_seed(self) -> int | None:
        raw = str(self._seed_entry.get_text() or "").strip()
        if not raw:
            return None
        if raw.startswith("-") and raw[1:].isdigit():
            return int(raw)
        if raw.isdigit():
            return int(raw)
        raise ValueError("Spin seed must be an integer.")

    def _set_controls_enabled(self, enabled: bool) -> None:
        self._seed_entry.set_sensitive(enabled)
        self._spin_button.set_sensitive(enabled)
        self._play_last_button.set_sensitive(enabled)

    def set_controls_enabled(self, enabled: bool) -> None:
        self._set_controls_enabled(bool(enabled))

    def set_compact_layout(self, stacked: bool) -> None:
        if not self._compact:
            return
        if bool(stacked):
            self._button_row.set_orientation(Gtk.Orientation.VERTICAL)
            self._button_row.set_spacing(4)
            self._button_row.set_halign(Gtk.Align.FILL)
            self._spin_button.set_hexpand(True)
            self._play_last_button.set_hexpand(True)
        else:
            self._button_row.set_orientation(Gtk.Orientation.HORIZONTAL)
            self._button_row.set_spacing(6)
            self._button_row.set_halign(Gtk.Align.END)
            self._spin_button.set_hexpand(False)
            self._play_last_button.set_hexpand(False)

    def _cancel_spin_animation(self) -> None:
        if self._spin_source_id is not None:
            try:
                GLib.source_remove(self._spin_source_id)
            except Exception:
                pass
            self._spin_source_id = None
        self._spin_payload = None
        self._spin_complete_callback = None
        self._spin_tick = 0
        self._set_controls_enabled(True)

    def start_spin_animation(
        self,
        *,
        on_complete: Callable[[dict[str, object]], None] | None = None,
    ) -> None:
        self._cancel_spin_animation()
        self._spin_payload = None
        self._spin_complete_callback = on_complete
        self._spin_tick = 0
        self._set_controls_enabled(False)
        self._selected_label.set_text("Selected: spinning...")
        self._selected_market_label.set_text("Selected Market: loading...")
        self._result_label.set_text("Status: spinning...")
        self._spin_source_id = GLib.timeout_add(
            self._SPIN_INTERVAL_MS,
            self._advance_spin_animation,
        )

    def complete_spin_animation(self, payload: dict[str, object]) -> None:
        if self._spin_source_id is None:
            self.set_spin_result(payload)
            return
        self._spin_payload = dict(payload)

    def animate_spin_result(
        self,
        payload: dict[str, object],
        *,
        on_complete: Callable[[dict[str, object]], None] | None = None,
    ) -> None:
        self.start_spin_animation(on_complete=on_complete)
        self.complete_spin_animation(payload)

    def _advance_spin_animation(self) -> bool:
        payload = self._spin_payload

        frame = self._SPIN_FRAMES[self._spin_tick % len(self._SPIN_FRAMES)]
        self._selected_label.set_text(f"Selected: spinning {frame}")

        if self._spin_tick % self._TEXT_UPDATE_EVERY == 0:
            message_step = (self._spin_tick // self._TEXT_UPDATE_EVERY) % len(
                self._SPIN_MESSAGES
            )
            dots = "." * (((self._spin_tick // self._TEXT_UPDATE_EVERY) % 3) + 1)
            self._result_label.set_text(f"{self._SPIN_MESSAGES[message_step]}{dots}")

        self._spin_tick += 1

        if payload is None:
            return True

        if self._spin_tick < self._SPIN_TICKS:
            return True

        callback = self._spin_complete_callback
        self._spin_source_id = None
        self._spin_complete_callback = None
        self._spin_payload = None
        self._spin_tick = 0
        self.set_spin_result(payload)
        if callback is not None:
            callback(payload)
        return False

    def set_spin_result(self, payload: dict[str, object]) -> None:
        self._cancel_spin_animation()
        release = payload.get("release")
        if isinstance(release, dict):
            release_id = release.get("discogs_release_id")
            artist = str(release.get("artist") or "Unknown Artist")
            title = str(release.get("title") or "Unknown Title")
            year = release.get("year")
            year_text = str(year) if year is not None else "Unknown Year"
            self._selected_label.set_text(
                f"Selected: #{release_id} {artist} - {title} ({year_text})"
            )
            self._selected_market_label.set_text(format_market_summary(release))
        else:
            self._selected_market_label.set_text("Selected Market: n/a")
        self._result_label.set_text(
            str(payload.get("status_message") or "Spin complete.")
        )

    def set_play_result(self, payload: dict[str, object]) -> None:
        self._cancel_spin_animation()
        self._result_label.set_text(
            str(payload.get("status_message") or "Play complete.")
        )

    def set_error(self, message: str) -> None:
        self._cancel_spin_animation()
        self._result_label.set_text(f"Error: {message}")
