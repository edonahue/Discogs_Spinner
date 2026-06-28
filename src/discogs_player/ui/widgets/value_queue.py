"""Value refresh queue widget — shows releases needing market price updates."""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from discogs_player.ui.utils.coerce import as_int as _as_int
from discogs_player.ui.utils.coerce import as_str as _as_str


def _reason_label(reason: str) -> str:
    if reason == "missing":
        return "No price data"
    if reason == "unpriced":
        return "Price row empty"
    if reason == "stale":
        return "Price stale"
    return reason


class ValueQueueWidget(Gtk.Box):
    def __init__(
        self,
        *,
        on_refresh: Callable[[], None] | None = None,
        on_release_selected: Callable[[int], None] | None = None,
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_margin_top(8)
        self.set_margin_bottom(8)
        self.set_margin_start(8)
        self.set_margin_end(8)
        self.set_hexpand(True)
        self.set_vexpand(True)

        self._on_refresh = on_refresh
        self._on_release_selected = on_release_selected

        # Header row
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.set_margin_bottom(8)

        title = Gtk.Label(label="Value Refresh Queue")
        title.add_css_class("ipod-section-header")
        title.set_xalign(0.0)
        title.set_hexpand(True)
        header.append(title)

        self._refresh_btn = Gtk.Button(label="Refresh")
        self._refresh_btn.add_css_class("suggested-action")
        self._refresh_btn.connect("clicked", self._on_refresh_clicked)
        header.append(self._refresh_btn)

        self.append(header)

        # Summary row
        self._summary_label = Gtk.Label(label="")
        self._summary_label.add_css_class("ipod-status")
        self._summary_label.set_xalign(0.0)
        self._summary_label.set_margin_bottom(8)
        self.append(self._summary_label)

        # List container
        self._list_box = Gtk.ListBox()
        self._list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self._list_box.add_css_class("boxed-list")
        self._list_box.set_hexpand(True)
        self.append(self._list_box)

        # Empty/loading state
        self._empty_label = Gtk.Label(label="No data loaded. Click Refresh.")
        self._empty_label.add_css_class("dim-label")
        self._empty_label.set_margin_top(24)
        self._empty_label.set_halign(Gtk.Align.CENTER)
        self.append(self._empty_label)

    def _on_refresh_clicked(self, _btn: Gtk.Button) -> None:
        if self._on_refresh:
            self._on_refresh()

    def set_busy(self, message: str = "Loading…") -> None:
        self._refresh_btn.set_sensitive(False)
        self._summary_label.set_text(message)

    def set_error(self, message: str) -> None:
        self._refresh_btn.set_sensitive(True)
        self._summary_label.set_text(f"Error: {message}")
        self._clear_list()
        self._empty_label.set_text("Failed to load queue.")
        self._empty_label.set_visible(True)

    def set_queue(self, report: dict[str, object]) -> None:
        self._refresh_btn.set_sensitive(True)

        total = _as_int(report.get("total_candidates"))
        missing = _as_int(report.get("missing_count"))
        unpriced = _as_int(report.get("unpriced_count"))
        stale = _as_int(report.get("stale_count"))
        limit = _as_int(report.get("limit"))

        summary_parts = [f"{total} candidate{'s' if total != 1 else ''} total"]
        if missing:
            summary_parts.append(f"{missing} missing")
        if unpriced:
            summary_parts.append(f"{unpriced} unpriced")
        if stale:
            summary_parts.append(f"{stale} stale")
        summary = " · ".join(summary_parts)
        if total > limit:
            summary += f" (showing top {limit})"
        self._summary_label.set_text(summary)

        queue_raw = report.get("queue")
        queue: list[dict[str, object]] = (
            [dict(item) for item in queue_raw if isinstance(item, dict)]
            if isinstance(queue_raw, list)
            else []
        )

        self._clear_list()

        if not queue:
            self._empty_label.set_text("Queue is empty — all prices up to date.")
            self._empty_label.set_visible(True)
            return

        self._empty_label.set_visible(False)

        for item in queue:
            row = self._build_row(item)
            self._list_box.append(row)

    def _clear_list(self) -> None:
        child = self._list_box.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            self._list_box.remove(child)
            child = next_child

    def _build_row(self, item: dict[str, object]) -> Gtk.Widget:
        release_id = _as_int(item.get("discogs_release_id"))
        artist = _as_str(item.get("artist"))
        title = _as_str(item.get("title"))
        reason = _as_str(item.get("market_need_reason"))
        last_updated = _as_str(item.get("market_last_updated_at"))

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.set_margin_top(6)
        row.set_margin_bottom(6)
        row.set_margin_start(8)
        row.set_margin_end(8)

        # Release info (left)
        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info.set_hexpand(True)

        name_text = f"{artist} — {title}" if artist and title else (artist or title or f"Release {release_id}")
        name_label = Gtk.Label(label=name_text)
        name_label.set_xalign(0.0)
        name_label.set_wrap(True)
        info.append(name_label)

        meta_parts = [_reason_label(reason)]
        if last_updated:
            meta_parts.append(f"last updated {last_updated[:10]}" if len(last_updated) >= 10 else f"last updated {last_updated}")
        meta_label = Gtk.Label(label=" · ".join(meta_parts))
        meta_label.set_xalign(0.0)
        meta_label.add_css_class("dim-label")
        meta_label.set_wrap(True)
        info.append(meta_label)

        row.append(info)

        # View button (right)
        if release_id and self._on_release_selected:
            view_btn = Gtk.Button(label="Open in Browse")
            view_btn.add_css_class("flat")
            rid = release_id
            view_btn.connect("clicked", lambda _b, r=rid: self._on_release_selected(r))  # type: ignore[misc]
            row.append(view_btn)

        return row
