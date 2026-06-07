"""Hidden Gems card for the Value workspace.

Surfaces owned releases that are both valuable AND currently scarce on the
Discogs marketplace — the kind of 'quietly worth money' items that the
default Discogs.com value display doesn't highlight.
"""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from discogs_player.ui.utils.formatting import format_price


def _as_int(value: object | None) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return int(text)
        except ValueError:
            return None
    try:
        if value is None:
            return None
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _as_float(value: object | None) -> float | None:
    try:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return None
            return float(text)
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _as_str(value: object | None) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _reasons_label(reasons: object | None) -> str:
    if not isinstance(reasons, list):
        return ""
    pretty = {
        "scarce-now": "Scarce now",
        "high-value": "High value",
        "surprising": "Surprising",
        "community-hot": "Community hot",
    }
    return " · ".join(pretty.get(str(r), str(r)) for r in reasons)


class HiddenGemsCard(Gtk.Box):
    def __init__(
        self,
        *,
        on_release_selected: Callable[[int], None] | None = None,
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_margin_top(4)
        self.set_margin_bottom(4)
        self.set_margin_start(4)
        self.set_margin_end(4)
        self.set_hexpand(True)
        self.add_css_class("ipod-panel")
        self.add_css_class("ipod-hidden-gems-card")

        self._on_release_selected = on_release_selected

        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        header.set_hexpand(True)
        self.append(header)

        title = Gtk.Label(label="Hidden Gems")
        title.set_xalign(0.0)
        title.add_css_class("title-4")
        header.append(title)

        subtitle = Gtk.Label(
            label=(
                "Owned releases that are quietly valuable AND hard to find on the "
                "Discogs marketplace right now."
            )
        )
        subtitle.set_xalign(0.0)
        subtitle.set_wrap(True)
        subtitle.add_css_class("dim-label")
        header.append(subtitle)

        self._status = Gtk.Label(label="Loading hidden gems…")
        self._status.set_xalign(0.0)
        self._status.set_wrap(True)
        self._status.add_css_class("dim-label")
        self.append(self._status)

        self._list = Gtk.ListBox()
        self._list.set_selection_mode(Gtk.SelectionMode.NONE)
        self._list.set_hexpand(True)
        self._list.add_css_class("boxed-list")
        self._list.connect("row-activated", self._handle_row_activated)
        self.append(self._list)

        self._row_to_release_id: dict[Gtk.ListBoxRow, int] = {}

    def set_loading(self, message: str = "Loading hidden gems…") -> None:
        self._status.set_text(message)
        self._status.set_visible(True)
        self._clear_list()

    def set_error(self, message: str) -> None:
        self._status.set_text(f"Hidden gems unavailable: {message}")
        self._status.set_visible(True)
        self._clear_list()

    def set_gems(self, report: dict[str, object]) -> None:
        self._clear_list()
        gems = report.get("gems") if isinstance(report, dict) else None
        if not isinstance(gems, list) or not gems:
            self._status.set_text(
                "No hidden gems above the current threshold. Try syncing stats "
                "or lowering the minimum median."
            )
            self._status.set_visible(True)
            return

        count = len(gems)
        self._status.set_text(
            f"Showing {count} release{'s' if count != 1 else ''} ranked by "
            f"value × scarcity."
        )
        self._status.set_visible(True)

        for item in gems:
            if not isinstance(item, dict):
                continue
            row = self._build_row(item)
            if row is not None:
                self._list.append(row)

    def _clear_list(self) -> None:
        child = self._list.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self._list.remove(child)
            child = nxt
        self._row_to_release_id = {}

    def _build_row(self, item: dict[str, object]) -> Gtk.ListBoxRow | None:
        release_id = _as_int(item.get("discogs_release_id"))
        if release_id is None:
            return None

        row = Gtk.ListBoxRow()
        row.set_activatable(True)
        self._row_to_release_id[row] = release_id

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        box.set_margin_start(8)
        box.set_margin_end(8)
        row.set_child(box)

        # Left: artist + title stacked
        text_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        text_col.set_hexpand(True)
        box.append(text_col)

        artist = _as_str(item.get("artist")) or "Unknown Artist"
        title = _as_str(item.get("title")) or "Unknown Title"
        artist_title = Gtk.Label(label=f"{artist} — {title}")
        artist_title.set_xalign(0.0)
        artist_title.set_wrap(True)
        artist_title.set_wrap_mode(2)
        artist_title.add_css_class("body")
        text_col.append(artist_title)

        reasons_text = _reasons_label(item.get("reasons"))
        year = _as_int(item.get("year"))
        meta_bits: list[str] = []
        if year:
            meta_bits.append(str(year))
        if reasons_text:
            meta_bits.append(reasons_text)
        if meta_bits:
            meta = Gtk.Label(label=" · ".join(meta_bits))
            meta.set_xalign(0.0)
            meta.set_wrap(True)
            meta.add_css_class("dim-label")
            text_col.append(meta)

        # Right: median + num_for_sale stacked
        stats_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        stats_col.set_valign(Gtk.Align.CENTER)
        box.append(stats_col)

        median = _as_float(item.get("market_median"))
        currency = _as_str(item.get("market_currency"))
        median_str = format_price(median, currency) if median is not None else "—"
        median_label = Gtk.Label(label=median_str)
        median_label.set_xalign(1.0)
        median_label.add_css_class("title-5")
        stats_col.append(median_label)

        n4s = _as_int(item.get("num_for_sale"))
        n4s_text = "0 for sale" if n4s == 0 else f"{n4s} for sale" if n4s is not None else "—"
        n4s_label = Gtk.Label(label=n4s_text)
        n4s_label.set_xalign(1.0)
        n4s_label.add_css_class("dim-label")
        stats_col.append(n4s_label)

        return row

    def _handle_row_activated(self, _list: Gtk.ListBox, row: Gtk.ListBoxRow) -> None:
        if self._on_release_selected is None:
            return
        release_id = self._row_to_release_id.get(row)
        if release_id is None:
            return
        self._on_release_selected(release_id)
