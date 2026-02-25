"""iPod-style text menu for browsing releases."""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Pango


class ReleaseTextMenu(Gtk.ScrolledWindow):
    def __init__(
        self,
        *,
        on_selection_changed: Callable[[dict[str, object] | None], None] | None = None,
    ) -> None:
        super().__init__()
        self.set_vexpand(True)
        self.set_hexpand(True)
        self.add_css_class("ipod-text-menu")
        self._on_selection_changed = on_selection_changed
        self._rows_to_items: dict[int, dict[str, object]] = {}
        self._release_ids_to_rows: dict[int, Gtk.ListBoxRow] = {}

        self._list = Gtk.ListBox()
        self._list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._list.add_css_class("navigation-sidebar")
        self._list.connect("row-selected", self._handle_row_selected)
        self.set_child(self._list)

    def _clear(self) -> None:
        row = self._list.get_first_child()
        while row is not None:
            next_row = row.get_next_sibling()
            self._list.remove(row)
            row = next_row
        self._rows_to_items.clear()
        self._release_ids_to_rows.clear()

    def _build_row(self, item: dict[str, object]) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()
        row.add_css_class("ipod-menu-row")

        outer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        outer.set_margin_top(4)
        outer.set_margin_bottom(4)
        outer.set_margin_start(8)
        outer.set_margin_end(8)

        text_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        text_col.set_hexpand(True)

        title = str(item.get("title") or "Unknown Title")
        artist = str(item.get("artist") or "Unknown Artist")
        year = item.get("year")
        genres = item.get("genres")
        primary = Gtk.Label(label=f"{artist} - {title}")
        primary.set_xalign(0.0)
        primary.set_wrap(True)
        primary.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        primary.add_css_class("ipod-menu-primary")

        genre_text = ""
        if isinstance(genres, list) and genres:
            first_genre = str(genres[0] or "").strip()
            if first_genre:
                genre_text = first_genre
        secondary_parts = [
            piece
            for piece in (str(year) if year is not None else "", genre_text)
            if piece
        ]
        secondary = Gtk.Label(label=" • ".join(secondary_parts))
        secondary.set_xalign(0.0)
        secondary.add_css_class("ipod-menu-secondary")

        text_col.append(primary)
        text_col.append(secondary)
        outer.append(text_col)

        chevron = Gtk.Label(label="›")
        chevron.add_css_class("ipod-menu-chevron")
        outer.append(chevron)

        row.set_child(outer)
        return row

    def set_items(self, items: list[dict[str, object]]) -> None:
        self._clear()
        for item in items:
            row = self._build_row(item)
            item_dict = dict(item)
            self._rows_to_items[id(row)] = item_dict
            release_id = item_dict.get("discogs_release_id")
            if isinstance(release_id, int):
                self._release_ids_to_rows[release_id] = row
            self._list.append(row)

        if items:
            first = self._list.get_row_at_index(0)
            if first is not None:
                self._list.select_row(first)
        elif self._on_selection_changed is not None:
            self._on_selection_changed(None)

    def _handle_row_selected(
        self, _list_box: Gtk.ListBox, row: Gtk.ListBoxRow | None
    ) -> None:
        if self._on_selection_changed is None:
            return
        if row is None:
            self._on_selection_changed(None)
            return
        item = self._rows_to_items.get(id(row))
        self._on_selection_changed(dict(item) if isinstance(item, dict) else None)

    def select_release(self, discogs_release_id: int) -> bool:
        row = self._release_ids_to_rows.get(int(discogs_release_id))
        if row is None:
            return False
        self._list.select_row(row)
        return True
