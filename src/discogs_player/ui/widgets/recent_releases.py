"""Recently added releases widget — filterable by time window."""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from discogs_player.ui.utils.coerce import as_str as _as_str


def _format_added_at(iso: object | None) -> str:
    if not iso:
        return "—"
    s = str(iso)
    return s[:10] if len(s) >= 10 else s


DAYS_OPTIONS = [("7 days", 7), ("30 days", 30), ("90 days", 90)]


class RecentReleasesWidget(Gtk.Box):
    def __init__(
        self,
        *,
        on_load: Callable[[int], None] | None = None,
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_margin_top(8)
        self.set_margin_bottom(8)
        self.set_margin_start(8)
        self.set_margin_end(8)
        self.set_hexpand(True)
        self.set_vexpand(True)

        self._on_load = on_load
        self._selected_days = 7

        # Header row
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.set_margin_bottom(12)

        title = Gtk.Label(label="Recently Added")
        title.add_css_class("ipod-section-header")
        title.set_xalign(0.0)
        title.set_hexpand(True)
        header.append(title)

        # Days filter dropdown
        days_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        for label, days in DAYS_OPTIONS:
            btn = Gtk.ToggleButton(label=label)
            if days == self._selected_days:
                btn.set_active(True)
            btn.connect("toggled", self._on_days_toggled, days)
            days_box.append(btn)
            setattr(self, f"_days_btn_{days}", btn)
        header.append(days_box)

        self.append(header)

        # List area
        self._list_box = Gtk.ListBox()
        self._list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self._list_box.add_css_class("boxed-list")
        self._list_box.set_hexpand(True)
        self.append(self._list_box)

        # Status label
        self._status_label = Gtk.Label(label="Loading…")
        self._status_label.add_css_class("dim-label")
        self._status_label.set_margin_top(16)
        self._status_label.set_halign(Gtk.Align.CENTER)
        self.append(self._status_label)

    def _on_days_toggled(self, btn: Gtk.ToggleButton, days: int) -> None:
        if not btn.get_active():
            return
        # Deactivate other buttons
        for _, d in DAYS_OPTIONS:
            if d != days:
                other = getattr(self, f"_days_btn_{d}", None)
                if other and other.get_active():
                    other.set_active(False)
        self._selected_days = days
        if self._on_load:
            self._on_load(days)

    def set_busy(self, message: str = "Loading…") -> None:
        self._clear_list()
        self._status_label.set_text(message)
        self._status_label.set_visible(True)

    def set_error(self, message: str) -> None:
        self._clear_list()
        self._status_label.set_text(f"Error: {message}")
        self._status_label.set_visible(True)

    def set_releases(self, data: dict[str, object]) -> None:
        self._clear_list()
        self._status_label.set_visible(False)

        releases_raw = data.get("releases")
        releases = (
            [r for r in releases_raw if isinstance(r, dict)]
            if isinstance(releases_raw, list)
            else []
        )

        if not releases:
            self._status_label.set_text("No releases added in this period.")
            self._status_label.set_visible(True)
            return

        for release in releases:
            row = self._build_row(release)
            self._list_box.append(row)

    def _build_row(self, release: dict[str, object]) -> Gtk.Widget:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row.set_margin_top(6)
        row.set_margin_bottom(6)
        row.set_margin_start(8)
        row.set_margin_end(8)

        # Artist — Title
        text_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        text_col.set_hexpand(True)

        artist_title = f"{_as_str(release.get('artist'), '—')} – {_as_str(release.get('title'), '—')}"
        main_lbl = Gtk.Label(label=artist_title)
        main_lbl.set_xalign(0.0)
        main_lbl.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
        text_col.append(main_lbl)

        year = _as_str(release.get("year"), "")
        if year:
            year_lbl = Gtk.Label(label=year)
            year_lbl.add_css_class("dim-label")
            year_lbl.add_css_class("caption")
            year_lbl.set_xalign(0.0)
            text_col.append(year_lbl)

        row.append(text_col)

        # Added date
        date_lbl = Gtk.Label(label=_format_added_at(release.get("added_at")))
        date_lbl.add_css_class("dim-label")
        date_lbl.add_css_class("caption")
        date_lbl.set_xalign(1.0)
        row.append(date_lbl)

        return row

    def _clear_list(self) -> None:
        child = self._list_box.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self._list_box.remove(child)
            child = nxt
