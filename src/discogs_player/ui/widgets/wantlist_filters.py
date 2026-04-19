"""Wantlist filter bar widget for the GUI."""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


class WantlistFilterBar(Gtk.Box):
    _SORT_OPTIONS: tuple[tuple[str, str], ...] = (
        ("artist_title", "Sort: Artist/Title"),
        ("year_desc", "Sort: Year (Newest)"),
        ("year_asc", "Sort: Year (Oldest)"),
        ("genre", "Sort: Genre (A-Z)"),
        ("genre_year", "Sort: Genre then Year"),
    )

    def __init__(
        self,
        *,
        default_limit: int | None = 0,
        on_refresh: Callable[[], None] | None = None,
        on_sync: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_hexpand(True)
        self.set_margin_top(8)
        self.set_margin_bottom(8)
        self.set_margin_start(8)
        self.set_margin_end(8)
        self._on_refresh = on_refresh
        self._on_sync = on_sync
        self._default_limit = self._normalize_limit(default_limit)

        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        top_row.set_hexpand(True)
        self._top_row = top_row
        self.append(top_row)

        bottom_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        bottom_row.set_hexpand(True)
        self._bottom_row = bottom_row
        self.append(bottom_row)
        self._compact_layout = False

        self._search_entry = Gtk.Entry()
        self._search_entry.set_hexpand(True)
        self._search_entry.set_width_chars(16)
        self._search_entry.set_placeholder_text("Search artist/title")
        top_row.append(self._search_entry)

        self._year_entry = Gtk.Entry()
        self._year_entry.set_width_chars(11)
        self._year_entry.set_placeholder_text("Year (e.g. 1990:1999)")
        top_row.append(self._year_entry)

        self._genre_entry = Gtk.Entry()
        self._genre_entry.set_hexpand(True)
        self._genre_entry.set_width_chars(16)
        self._genre_entry.set_placeholder_text("Genres (comma-separated)")
        top_row.append(self._genre_entry)

        self._style_entry = Gtk.Entry()
        self._style_entry.set_hexpand(True)
        self._style_entry.set_width_chars(16)
        self._style_entry.set_placeholder_text("Styles (comma-separated)")
        top_row.append(self._style_entry)

        self._sort_values = [item[0] for item in self._SORT_OPTIONS]
        self._sort_dropdown = Gtk.DropDown.new_from_strings(
            [item[1] for item in self._SORT_OPTIONS]
        )
        self._sort_dropdown.set_hexpand(True)
        self._sort_dropdown.set_selected(0)
        self._sort_dropdown.connect(
            "notify::selected", lambda *_: self._trigger_refresh()
        )
        bottom_row.append(self._sort_dropdown)

        self._limit_spin = Gtk.SpinButton()
        self._limit_spin.set_numeric(True)
        self._limit_spin.set_range(0, 10000)
        self._limit_spin.set_increments(1, 25)
        self._limit_spin.set_value(self._default_limit)
        self._limit_spin.set_tooltip_text("Result limit (0 = all)")
        bottom_row.append(self._limit_spin)

        clear_button = Gtk.Button(label="Clear")
        clear_button.connect("clicked", lambda *_: self.clear())
        self._clear_button = clear_button
        bottom_row.append(clear_button)

        refresh_button = Gtk.Button(label="Refresh")
        if self._on_refresh is not None:
            refresh_button.connect("clicked", lambda *_: self._on_refresh())
        self._refresh_button = refresh_button
        bottom_row.append(refresh_button)

        sync_button = Gtk.Button(label="Sync Wantlist")
        if self._on_sync is not None:
            sync_button.connect("clicked", lambda *_: self._on_sync())
        self._sync_button = sync_button
        self._sync_button.set_sensitive(self._on_sync is not None)
        bottom_row.append(sync_button)

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

    @staticmethod
    def _normalize_limit(value: int | None) -> int:
        if value is None:
            return 0
        return max(0, int(value))

    def clear(self) -> None:
        self._search_entry.set_text("")
        self._year_entry.set_text("")
        self._genre_entry.set_text("")
        self._style_entry.set_text("")
        self._sort_dropdown.set_selected(0)
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

    def limit(self) -> int:
        return self._normalize_limit(self._limit_spin.get_value_as_int())

    def sort_mode(self) -> str:
        selected = int(self._sort_dropdown.get_selected())
        if selected < 0 or selected >= len(self._sort_values):
            return "artist_title"
        return self._sort_values[selected]

    def current_filters(self) -> dict[str, object]:
        return {
            "q": self.search_text(),
            "year": self.year_text(),
            "genres": self.genres(),
            "styles": self.styles(),
            "sort": self.sort_mode(),
            "limit": self.limit(),
        }

    def set_compact_layout(self, compact: bool) -> None:
        compact_layout = bool(compact)
        if self._compact_layout == compact_layout:
            return
        self._compact_layout = compact_layout

        orientation = (
            Gtk.Orientation.VERTICAL
            if compact_layout
            else Gtk.Orientation.HORIZONTAL
        )
        spacing = 6 if compact_layout else 8
        for row in (self._top_row, self._bottom_row):
            row.set_orientation(orientation)
            row.set_spacing(spacing)

        fill_widgets = (
            self._search_entry,
            self._year_entry,
            self._genre_entry,
            self._style_entry,
            self._sort_dropdown,
            self._limit_spin,
            self._clear_button,
            self._refresh_button,
            self._sync_button,
        )
        for widget in fill_widgets:
            widget.set_hexpand(compact_layout)

    def set_sync_enabled(self, enabled: bool) -> None:
        self._sync_button.set_sensitive(bool(enabled) and self._on_sync is not None)
