"""Filter controls for the release grid."""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


class FilterBar(Gtk.Box):
    def __init__(
        self,
        *,
        default_limit: int = 50,
        on_refresh: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.set_margin_top(8)
        self.set_margin_bottom(8)
        self.set_margin_start(8)
        self.set_margin_end(8)
        self._on_refresh = on_refresh
        self._default_limit = max(1, int(default_limit))

        self._search_entry = Gtk.Entry()
        self._search_entry.set_hexpand(False)
        self._search_entry.set_width_chars(18)
        self._search_entry.set_placeholder_text("Search artist/title")
        self.append(self._search_entry)

        self._year_entry = Gtk.Entry()
        self._year_entry.set_width_chars(12)
        self._year_entry.set_placeholder_text("Year (e.g. 1990:1999)")
        self.append(self._year_entry)

        self._genre_entry = Gtk.Entry()
        self._genre_entry.set_hexpand(True)
        self._genre_entry.set_width_chars(18)
        self._genre_entry.set_placeholder_text("Genres (comma-separated)")
        self.append(self._genre_entry)

        self._style_entry = Gtk.Entry()
        self._style_entry.set_hexpand(True)
        self._style_entry.set_width_chars(18)
        self._style_entry.set_placeholder_text("Styles (comma-separated)")
        self.append(self._style_entry)

        self._unmatched_only = Gtk.CheckButton(label="Unmatched")
        self.append(self._unmatched_only)

        self._limit_spin = Gtk.SpinButton()
        self._limit_spin.set_numeric(True)
        self._limit_spin.set_range(1, 500)
        self._limit_spin.set_increments(1, 25)
        self._limit_spin.set_value(self._default_limit)
        self._limit_spin.set_tooltip_text("Result limit")
        self.append(self._limit_spin)

        clear_button = Gtk.Button(label="Clear")
        clear_button.connect("clicked", lambda *_: self.clear())
        self.append(clear_button)

        refresh_button = Gtk.Button(label="Refresh")
        if self._on_refresh is not None:
            refresh_button.connect("clicked", lambda *_: self._on_refresh())
        self.append(refresh_button)

        for entry in (
            self._search_entry,
            self._year_entry,
            self._genre_entry,
            self._style_entry,
        ):
            entry.connect("activate", lambda *_: self._trigger_refresh())

    def _trigger_refresh(self) -> None:
        if self._on_refresh is not None:
            self._on_refresh()

    @staticmethod
    def _parse_csv(raw: str) -> list[str]:
        values: list[str] = []
        for piece in raw.split(","):
            value = piece.strip()
            if value:
                values.append(value)
        return values

    def clear(self) -> None:
        self._search_entry.set_text("")
        self._year_entry.set_text("")
        self._genre_entry.set_text("")
        self._style_entry.set_text("")
        self._unmatched_only.set_active(False)
        self._limit_spin.set_value(self._default_limit)
        self._trigger_refresh()

    def search_text(self) -> str | None:
        text = str(self._search_entry.get_text() or "").strip()
        return text or None

    def year_text(self) -> str | None:
        text = str(self._year_entry.get_text() or "").strip()
        return text or None

    def genres(self) -> list[str]:
        return self._parse_csv(str(self._genre_entry.get_text() or ""))

    def styles(self) -> list[str]:
        return self._parse_csv(str(self._style_entry.get_text() or ""))

    def unmatched(self) -> bool:
        return bool(self._unmatched_only.get_active())

    def limit(self) -> int:
        return max(1, int(self._limit_spin.get_value_as_int()))

    def current_filters(self) -> dict[str, object]:
        return {
            "q": self.search_text(),
            "year": self.year_text(),
            "genres": self.genres(),
            "styles": self.styles(),
            "unmatched": self.unmatched(),
            "limit": self.limit(),
        }
