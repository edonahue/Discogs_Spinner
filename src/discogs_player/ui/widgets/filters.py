"""Simple filter controls for the release grid."""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


class FilterBar(Gtk.Box):
    def __init__(self, on_refresh: Callable[[], None] | None = None) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.set_margin_top(8)
        self.set_margin_bottom(8)
        self.set_margin_start(8)
        self.set_margin_end(8)

        self._search_entry = Gtk.Entry()
        self._search_entry.set_hexpand(True)
        self._search_entry.set_placeholder_text("Search artist/title")
        self.append(self._search_entry)

        refresh_button = Gtk.Button(label="Refresh")
        if on_refresh is not None:
            refresh_button.connect("clicked", lambda *_: on_refresh())
        self.append(refresh_button)

    def search_text(self) -> str | None:
        text = str(self._search_entry.get_text() or "").strip()
        return text or None

