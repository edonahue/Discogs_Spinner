"""Cover-grid widget for browsing releases."""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Pango


class CoverGrid(Gtk.ScrolledWindow):
    def __init__(
        self,
        *,
        on_selection_changed: Callable[[dict[str, object] | None], None] | None = None,
    ) -> None:
        super().__init__()
        self.set_vexpand(True)
        self.set_hexpand(True)
        self._on_selection_changed = on_selection_changed
        self._children_to_items: dict[int, dict[str, object]] = {}

        self._flow = Gtk.FlowBox()
        self._flow.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._flow.set_max_children_per_line(6)
        self._flow.set_min_children_per_line(2)
        self._flow.set_row_spacing(10)
        self._flow.set_column_spacing(10)
        self._flow.set_margin_top(8)
        self._flow.set_margin_bottom(8)
        self._flow.set_margin_start(8)
        self._flow.set_margin_end(8)
        self._flow.connect("selected-children-changed", self._handle_selection_changed)
        self.set_child(self._flow)

    def _clear(self) -> None:
        child = self._flow.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            self._flow.remove(child)
            child = next_child
        self._children_to_items.clear()

    def _build_card(self, item: dict[str, object]) -> Gtk.Widget:
        frame = Gtk.Frame()
        frame.set_size_request(190, 260)

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card.set_margin_top(6)
        card.set_margin_bottom(6)
        card.set_margin_start(6)
        card.set_margin_end(6)

        cover_path = str(item.get("cover_path") or "").strip()
        if cover_path:
            picture = Gtk.Picture.new_for_filename(cover_path)
            picture.set_can_shrink(True)
            picture.set_size_request(176, 176)
            picture.set_content_fit(Gtk.ContentFit.COVER)
            card.append(picture)
        else:
            placeholder = Gtk.Image.new_from_icon_name("media-optical-symbolic")
            placeholder.set_pixel_size(64)
            card.append(placeholder)

        title = Gtk.Label(label=str(item.get("title") or "Unknown Title"))
        title.set_xalign(0.0)
        title.set_wrap(True)
        title.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        title.add_css_class("heading")
        card.append(title)

        subtitle_parts = [str(item.get("artist") or "Unknown Artist")]
        year = item.get("year")
        if year is not None:
            subtitle_parts.append(str(year))
        subtitle = Gtk.Label(label=" - ".join(subtitle_parts))
        subtitle.set_xalign(0.0)
        subtitle.add_css_class("dim-label")
        subtitle.set_wrap(True)
        card.append(subtitle)

        frame.set_child(card)
        return frame

    def set_items(self, items: list[dict[str, object]]) -> None:
        self._clear()
        for item in items:
            card = self._build_card(item)
            child = Gtk.FlowBoxChild()
            child.set_child(card)
            self._children_to_items[id(child)] = dict(item)
            self._flow.insert(child, -1)

        if items:
            first = self._flow.get_child_at_index(0)
            if first is not None:
                self._flow.select_child(first)
        elif self._on_selection_changed is not None:
            self._on_selection_changed(None)

    def _handle_selection_changed(self, flow: Gtk.FlowBox) -> None:
        if self._on_selection_changed is None:
            return

        selected = flow.get_selected_children()
        if not selected:
            self._on_selection_changed(None)
            return

        item = self._children_to_items.get(id(selected[0]))
        self._on_selection_changed(dict(item) if isinstance(item, dict) else None)
