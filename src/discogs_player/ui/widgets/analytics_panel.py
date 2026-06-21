"""Collection analytics widget — genres, artists, styles, and year breakdowns."""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from discogs_player.ui.utils.coerce import as_int as _as_int
from discogs_player.ui.utils.coerce import as_str as _as_str


class AnalyticsPanelWidget(Gtk.Box):
    def __init__(
        self,
        *,
        on_refresh: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_margin_top(8)
        self.set_margin_bottom(8)
        self.set_margin_start(8)
        self.set_margin_end(8)
        self.set_hexpand(True)
        self.set_vexpand(True)

        self._on_refresh = on_refresh

        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.set_margin_bottom(12)

        title = Gtk.Label(label="Collection Analytics")
        title.add_css_class("ipod-section-header")
        title.set_xalign(0.0)
        title.set_hexpand(True)
        header.append(title)

        self._refresh_btn = Gtk.Button(label="Refresh")
        self._refresh_btn.add_css_class("suggested-action")
        self._refresh_btn.connect("clicked", self._on_refresh_clicked)
        header.append(self._refresh_btn)
        self.append(header)

        # Summary stat cards
        self._stats_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._stats_box.set_margin_bottom(16)
        self.append(self._stats_box)

        self._stat_active = self._make_stat_card("Active", "—")
        self._stat_mapped = self._make_stat_card("Mapped", "—")
        self._stat_unmatched = self._make_stat_card("Unmatched", "—")
        self._stat_rate = self._make_stat_card("Map rate", "—")
        for card in (self._stat_active, self._stat_mapped, self._stat_unmatched, self._stat_rate):
            self._stats_box.append(card[0])

        # Rank tables grid (2-column)
        self._tables_grid = Gtk.Grid()
        self._tables_grid.set_row_spacing(12)
        self._tables_grid.set_column_spacing(12)
        self._tables_grid.set_column_homogeneous(True)
        self.append(self._tables_grid)

        # Year tables below
        self._year_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self._year_box.set_margin_top(12)
        self.append(self._year_box)

        # Status label
        self._status_label = Gtk.Label(label="Loading…")
        self._status_label.add_css_class("dim-label")
        self._status_label.set_margin_top(16)
        self._status_label.set_halign(Gtk.Align.CENTER)
        self.append(self._status_label)

    def _make_stat_card(self, label: str, value: str) -> tuple[Gtk.Widget, Gtk.Label]:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.add_css_class("card")
        box.set_hexpand(True)
        box.set_margin_start(2)
        box.set_margin_end(2)
        box.set_margin_bottom(4)

        val_lbl = Gtk.Label(label=value)
        val_lbl.add_css_class("title-2")
        val_lbl.set_halign(Gtk.Align.CENTER)
        box.append(val_lbl)

        cap_lbl = Gtk.Label(label=label)
        cap_lbl.add_css_class("dim-label")
        cap_lbl.add_css_class("caption")
        cap_lbl.set_halign(Gtk.Align.CENTER)
        box.append(cap_lbl)

        return box, val_lbl

    def _on_refresh_clicked(self, _btn: Gtk.Button) -> None:
        if self._on_refresh:
            self._on_refresh()

    def set_busy(self, message: str = "Loading…") -> None:
        self._refresh_btn.set_sensitive(False)
        self._status_label.set_text(message)
        self._status_label.set_visible(True)

    def set_error(self, message: str) -> None:
        self._refresh_btn.set_sensitive(True)
        self._status_label.set_text(f"Error: {message}")
        self._status_label.set_visible(True)

    def set_analytics(self, data: dict[str, object]) -> None:
        self._refresh_btn.set_sensitive(True)
        self._status_label.set_visible(False)

        active = _as_int(data.get("release_count_active"))
        mapped = _as_int(data.get("mapped_count"))
        unmatched = _as_int(data.get("unmatched_count"))
        rate = f"{round(mapped / active * 100)}%" if active > 0 else "—"

        self._stat_active[1].set_text(str(active))
        self._stat_mapped[1].set_text(str(mapped))
        self._stat_unmatched[1].set_text(str(unmatched))
        self._stat_rate[1].set_text(rate)

        # Clear previous rank tables
        child = self._tables_grid.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self._tables_grid.remove(child)
            child = nxt

        rank_tables = [
            ("Top Genres", data.get("top_genres") or [], "genre"),
            ("Top Styles", data.get("top_styles") or [], "style"),
            ("Top Artists", data.get("top_artists") or [], "artist"),
        ]
        col = 0
        for title, rows_raw, label_key in rank_tables:
            rows = [r for r in rows_raw if isinstance(r, dict)]
            widget = self._build_rank_table(title, rows, label_key)
            self._tables_grid.attach(widget, col % 2, col // 2, 1, 1)
            col += 1

        # Year tables
        child = self._year_box.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self._year_box.remove(child)
            child = nxt

        year_tables = [
            ("By Release Year", data.get("by_release_year") or []),
            ("Acquisition Timeline", data.get("acquisition_timeline") or []),
        ]
        for title, rows_raw in year_tables:
            rows = [r for r in rows_raw if isinstance(r, dict)]
            widget = self._build_year_table(title, rows)
            widget.set_hexpand(True)
            self._year_box.append(widget)

    def _build_rank_table(
        self, title: str, rows: list[dict[str, object]], label_key: str
    ) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.add_css_class("card")
        box.set_hexpand(True)

        heading = Gtk.Label(label=title)
        heading.add_css_class("heading")
        heading.set_xalign(0.0)
        heading.set_margin_start(8)
        heading.set_margin_top(8)
        heading.set_margin_bottom(4)
        box.append(heading)

        if not rows:
            empty = Gtk.Label(label="No data.")
            empty.add_css_class("dim-label")
            empty.set_xalign(0.0)
            empty.set_margin_start(8)
            empty.set_margin_bottom(8)
            box.append(empty)
            return box

        for i, row in enumerate(rows):
            row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            row_box.set_margin_start(8)
            row_box.set_margin_end(8)
            row_box.set_margin_top(2)
            row_box.set_margin_bottom(2)

            rank_lbl = Gtk.Label(label=str(i + 1))
            rank_lbl.add_css_class("dim-label")
            rank_lbl.add_css_class("caption")
            rank_lbl.set_xalign(1.0)
            rank_lbl.set_size_request(18, -1)
            row_box.append(rank_lbl)

            name_lbl = Gtk.Label(label=_as_str(row.get(label_key), "—"))
            name_lbl.set_xalign(0.0)
            name_lbl.set_hexpand(True)
            name_lbl.set_ellipsize(3)
            row_box.append(name_lbl)

            count_lbl = Gtk.Label(label=str(_as_int(row.get("count"))))
            count_lbl.add_css_class("dim-label")
            count_lbl.set_xalign(1.0)
            row_box.append(count_lbl)

            box.append(row_box)

        box.set_margin_bottom(8)
        return box

    def _build_year_table(self, title: str, rows: list[dict[str, object]]) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.add_css_class("card")

        heading = Gtk.Label(label=title)
        heading.add_css_class("heading")
        heading.set_xalign(0.0)
        heading.set_margin_start(8)
        heading.set_margin_top(8)
        heading.set_margin_bottom(4)
        box.append(heading)

        if not rows:
            empty = Gtk.Label(label="No data.")
            empty.add_css_class("dim-label")
            empty.set_xalign(0.0)
            empty.set_margin_start(8)
            empty.set_margin_bottom(8)
            box.append(empty)
            return box

        for row in rows:
            row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            row_box.set_margin_start(8)
            row_box.set_margin_end(8)
            row_box.set_margin_top(2)
            row_box.set_margin_bottom(2)

            year_lbl = Gtk.Label(label=_as_str(row.get("year"), "—"))
            year_lbl.set_xalign(0.0)
            year_lbl.set_hexpand(True)
            row_box.append(year_lbl)

            count_lbl = Gtk.Label(label=str(_as_int(row.get("count"))))
            count_lbl.add_css_class("dim-label")
            count_lbl.set_xalign(1.0)
            row_box.append(count_lbl)

            box.append(row_box)

        box.set_margin_bottom(8)
        return box
