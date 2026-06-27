"""Home dashboard widget — collector insights, hidden gems, and summary stats."""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


def _as_str(value: object | None) -> str:
    if value is None:
        return "—"
    return str(value).strip() or "—"


def _as_int(value: object | None) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0


class HomeDashboardWidget(Gtk.Box):
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

        title = Gtk.Label(label="Home")
        title.add_css_class("ipod-section-header")
        title.set_xalign(0.0)
        title.set_hexpand(True)
        header.append(title)

        self._refresh_btn = Gtk.Button(label="Refresh")
        self._refresh_btn.add_css_class("suggested-action")
        self._refresh_btn.connect("clicked", self._on_refresh_clicked)
        header.append(self._refresh_btn)
        self.append(header)

        # Summary stat cards row
        self._stats_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._stats_box.set_margin_bottom(16)
        self.append(self._stats_box)

        self._stat_releases = self._make_stat_card("Records", "—")
        self._stat_health = self._make_stat_card("Health", "—")
        self._stat_mapped = self._make_stat_card("Mapped", "—")
        self._stat_wantlist = self._make_stat_card("Wantlist", "—")
        for card in (self._stat_releases, self._stat_health, self._stat_mapped, self._stat_wantlist):
            self._stats_box.append(card[0])

        # Highlights section
        highlights_label = Gtk.Label(label="Collector Insights")
        highlights_label.add_css_class("heading")
        highlights_label.set_xalign(0.0)
        highlights_label.set_margin_bottom(6)
        self.append(highlights_label)

        self._highlights_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self._highlights_box.set_margin_bottom(16)
        self.append(self._highlights_box)

        # Hidden gems section
        gems_label = Gtk.Label(label="Hidden Gems")
        gems_label.add_css_class("heading")
        gems_label.set_xalign(0.0)
        gems_label.set_margin_bottom(6)
        self.append(gems_label)

        self._gems_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.append(self._gems_box)

        # Status / loading label
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

    def set_insights(self, data: dict[str, object]) -> None:
        self._refresh_btn.set_sensitive(True)
        self._status_label.set_visible(False)

        summary = data.get("summary") or {}
        if not isinstance(summary, dict):
            summary = {}

        # Update stat cards
        releases = _as_int(summary.get("release_count_active"))
        health = _as_int(summary.get("health_score"))
        mapped = _as_int(summary.get("mapped_count"))
        wantlist = _as_int(summary.get("wantlist_count"))

        self._stat_releases[1].set_text(str(releases))
        self._stat_health[1].set_text(f"{health}/100")
        self._stat_mapped[1].set_text(str(mapped))
        self._stat_wantlist[1].set_text(str(wantlist))

        # Highlights
        self._clear_box(self._highlights_box)
        highlights_raw = data.get("highlights")
        highlights = (
            [h for h in highlights_raw if isinstance(h, dict)]
            if isinstance(highlights_raw, list)
            else []
        )
        if highlights:
            for h in highlights[:5]:
                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                msg_lbl = Gtk.Label(label=_as_str(h.get("message") or h.get("title")))
                msg_lbl.set_xalign(0.0)
                msg_lbl.set_wrap(True)
                msg_lbl.set_hexpand(True)
                row.append(msg_lbl)
                self._highlights_box.append(row)
        else:
            placeholder = Gtk.Label(label="No insights yet.")
            placeholder.add_css_class("dim-label")
            placeholder.set_xalign(0.0)
            self._highlights_box.append(placeholder)

        # Hidden gems
        self._clear_box(self._gems_box)
        gems_raw = data.get("top_hidden_gems")
        gems = (
            [g for g in gems_raw if isinstance(g, dict)]
            if isinstance(gems_raw, list)
            else []
        )
        if gems:
            for gem in gems:
                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
                artist_title = f"{_as_str(gem.get('artist'))} – {_as_str(gem.get('title'))}"
                lbl = Gtk.Label(label=artist_title)
                lbl.set_xalign(0.0)
                lbl.set_hexpand(True)
                lbl.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
                row.append(lbl)

                median = gem.get("market_median")
                if median is not None:
                    try:
                        price_lbl = Gtk.Label(label=f"${float(median):.0f}")
                        price_lbl.add_css_class("dim-label")
                        row.append(price_lbl)
                    except (TypeError, ValueError):
                        pass

                self._gems_box.append(row)
        else:
            placeholder = Gtk.Label(label="No hidden gems found.")
            placeholder.add_css_class("dim-label")
            placeholder.set_xalign(0.0)
            self._gems_box.append(placeholder)

    def _clear_box(self, box: Gtk.Box) -> None:
        child = box.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            box.remove(child)
            child = nxt
