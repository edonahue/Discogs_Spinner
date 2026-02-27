"""Filter controls for the release grid."""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


class FilterBar(Gtk.Box):
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
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_hexpand(True)
        self.set_margin_top(8)
        self.set_margin_bottom(8)
        self.set_margin_start(8)
        self.set_margin_end(8)
        self._on_refresh = on_refresh
        self._default_limit = self._normalize_limit(default_limit)

        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        top_row.set_hexpand(True)
        self.append(top_row)

        bottom_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        bottom_row.set_hexpand(True)
        self.append(bottom_row)

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

        self._unmatched_only = Gtk.CheckButton(label="Unmatched")
        bottom_row.append(self._unmatched_only)

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

        recent_button = Gtk.Button(label="Recent")
        recent_button.set_tooltip_text("Show releases added in last 30 days")
        recent_button.connect("clicked", lambda *_: self._apply_recent_filter())
        bottom_row.append(recent_button)

        clear_button = Gtk.Button(label="Clear")
        clear_button.connect("clicked", lambda *_: self.clear())
        bottom_row.append(clear_button)

        refresh_button = Gtk.Button(label="Refresh")
        if self._on_refresh is not None:
            refresh_button.connect("clicked", lambda *_: self._on_refresh())
        bottom_row.append(refresh_button)

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

    def _apply_recent_filter(self) -> None:
        """Apply filter for recently added releases (last 30 days)."""
        from datetime import datetime, timedelta, timezone

        # Calculate date 30 days ago
        recent_date = datetime.now(timezone.utc) - timedelta(days=30)
        year_str = str(recent_date.year)

        # Clear other filters
        self._search_entry.set_text("")
        self._genre_entry.set_text("")
        self._style_entry.set_text("")
        self._unmatched_only.set_active(False)

        # Set year filter to current year (as a proxy for recent)
        # and sort by added date (not directly available, so use year desc)
        self._year_entry.set_text(year_str)
        self._limit_spin.set_value(50)
        self._sort_dropdown.set_selected(1)  # year_desc

        self._trigger_refresh()

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
        self._unmatched_only.set_active(False)
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

    def unmatched(self) -> bool:
        return bool(self._unmatched_only.get_active())

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
            "unmatched": self.unmatched(),
            "sort": self.sort_mode(),
            "limit": self.limit(),
        }
