"""Gallery cover-grid widget used by browse and wantlist sections."""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk, Pango

from discogs_player.performance import performance_profile
from discogs_player.services.image_cache import ensure_cover_path_for_gtk

_GRID_GAP = 12
_GRID_MARGIN = 12
_TARGET_VISIBLE_ROWS = 3
_MIN_COLUMNS = 3
_MAX_COLUMNS = 8
_CARD_MIN_WIDTH = 148
_CARD_MAX_WIDTH = 312
_CARD_TEXT_HEIGHT = 74
_RESIZE_DEBOUNCE_MS = 36


class CoverGrid(Gtk.Box):
    def __init__(
        self,
        *,
        on_selection_changed: Callable[[dict[str, object] | None], None] | None = None,
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_vexpand(True)
        self.set_hexpand(True)
        self.set_focusable(True)
        self.add_css_class("ipod-gallery")
        self._on_selection_changed = on_selection_changed

        self._items: list[dict[str, object]] = []
        self._rendered_count = 0
        self._pending_append_source_id: int | None = None
        self._background_suspended = False
        self._perf = performance_profile()
        self._selected_release_id: int | None = None
        self._button_to_item: dict[int, dict[str, object]] = {}
        self._buttons_by_id: dict[int, Gtk.Button] = {}
        self._release_id_to_button: dict[int, Gtk.Button] = {}
        self._button_to_frame: dict[int, Gtk.Frame] = {}
        self._button_to_media: dict[int, Gtk.Widget] = {}
        self._selected_button_id: int | None = None

        self._layout_width = 0
        self._layout_height = 0
        self._reserved_right_width = 0
        self._card_width = 0
        self._cover_size = 0
        self._columns = _MIN_COLUMNS
        self._pending_layout_source_id: int | None = None

        self._scroll = Gtk.ScrolledWindow()
        self._scroll.set_hexpand(True)
        self._scroll.set_vexpand(True)
        self._scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.append(self._scroll)

        self._flow = Gtk.FlowBox()
        self._flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self._flow.set_homogeneous(False)
        self._flow.set_row_spacing(_GRID_GAP)
        self._flow.set_column_spacing(_GRID_GAP)
        self._flow.set_margin_top(_GRID_MARGIN)
        self._flow.set_margin_bottom(_GRID_MARGIN)
        self._flow.set_margin_start(_GRID_MARGIN)
        self._flow.set_margin_end(_GRID_MARGIN)
        self._flow.set_min_children_per_line(_MIN_COLUMNS)
        self._flow.set_max_children_per_line(_MIN_COLUMNS)
        self._flow.set_valign(Gtk.Align.START)
        self._flow.add_css_class("ipod-gallery-grid")
        self._scroll.set_child(self._flow)
        vadjustment = self._scroll.get_vadjustment()
        if vadjustment is not None:
            vadjustment.connect("value-changed", self._handle_scroll_position_changed)

        self.connect("notify::width", self._handle_size_change)
        self.connect("notify::height", self._handle_size_change)
        self.connect("destroy", self._handle_destroy)
        self._apply_responsive_layout()

    def set_background_suspended(self, suspended: bool) -> None:
        self._background_suspended = bool(suspended)
        if self._background_suspended:
            if self._pending_append_source_id is not None:
                GLib.source_remove(self._pending_append_source_id)
                self._pending_append_source_id = None
            self._cancel_pending_responsive_layout()
            return
        if self._rendered_count < len(self._items):
            self._schedule_append_next_chunk()

    def idle_debug_state(self) -> dict[str, object]:
        return {
            "background_suspended": self._background_suspended,
            "rendered_count": self._rendered_count,
            "item_count": len(self._items),
            "append_pending": self._pending_append_source_id is not None,
            "layout_pending": self._pending_layout_source_id is not None,
        }

    @staticmethod
    def _build_placeholder(
        *,
        icon_size: int,
        caption: str = "",
    ) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_halign(Gtk.Align.CENTER)
        box.set_valign(Gtk.Align.CENTER)
        image = Gtk.Image.new_from_icon_name("media-record-symbolic")
        if image.get_paintable() is None:
            image = Gtk.Image.new_from_icon_name("media-optical-symbolic")
        image.set_pixel_size(icon_size)
        image.add_css_class("ipod-cover-placeholder")
        image.add_css_class("ipod-gallery-placeholder")
        box.append(image)
        if caption:
            label = Gtk.Label(label=caption)
            label.set_halign(Gtk.Align.CENTER)
            label.add_css_class("ipod-gallery-placeholder-caption")
            box.append(label)
        return box

    def _build_cover_media(
        self,
        item: dict[str, object],
        *,
        size: int,
        placeholder_caption: str,
    ) -> Gtk.Widget:
        cover_url = str(item.get("cover_url") or "").strip() or None
        current_cover_path = str(item.get("cover_path") or "").strip() or None
        cover_path = ensure_cover_path_for_gtk(
            cover_url,
            current_cover_path,
        )
        if cover_path:
            item["cover_path"] = cover_path
        if cover_path:
            picture = Gtk.Picture.new_for_filename(cover_path)
            picture.set_can_shrink(True)
            picture.set_content_fit(Gtk.ContentFit.COVER)
            picture.set_size_request(size, size)
            return picture
        icon_size = max(48, int(size * 0.24))
        return self._build_placeholder(icon_size=icon_size, caption=placeholder_caption)

    def _clear(self) -> None:
        if self._pending_append_source_id is not None:
            GLib.source_remove(self._pending_append_source_id)
            self._pending_append_source_id = None
        child = self._flow.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            self._flow.remove(child)
            child = next_child
        self._button_to_item.clear()
        self._buttons_by_id.clear()
        self._release_id_to_button.clear()
        self._button_to_frame.clear()
        self._button_to_media.clear()
        self._selected_button_id = None
        self._rendered_count = 0

    def _append_items_until(self, target_count: int) -> None:
        normalized_target = min(len(self._items), max(0, int(target_count)))
        while self._rendered_count < normalized_target:
            item = self._items[self._rendered_count]
            self._flow.append(self._build_card(item))
            self._rendered_count += 1

    def _append_next_chunk(self) -> bool:
        self._pending_append_source_id = None
        if self._background_suspended:
            return False
        if self._rendered_count >= len(self._items):
            return False
        chunk_size = max(1, int(self._perf.gallery_chunk_items))
        self._append_items_until(self._rendered_count + chunk_size)
        self._apply_responsive_layout()
        return False

    def _schedule_append_next_chunk(self) -> None:
        if self._background_suspended:
            return
        if self._pending_append_source_id is not None:
            return
        if self._rendered_count >= len(self._items):
            return
        self._pending_append_source_id = GLib.idle_add(self._append_next_chunk)

    def _ensure_release_rendered(self, discogs_release_id: int) -> bool:
        if int(discogs_release_id) in self._release_id_to_button:
            return True
        target_index: int | None = None
        for index, item in enumerate(self._items):
            if item.get("discogs_release_id") == int(discogs_release_id):
                target_index = index
                break
        if target_index is None:
            return False
        self._append_items_until(target_index + 1)
        self._apply_responsive_layout()
        return int(discogs_release_id) in self._release_id_to_button

    def _handle_scroll_position_changed(self, adjustment: object) -> None:
        get_value = getattr(adjustment, "get_value", None)
        get_page_size = getattr(adjustment, "get_page_size", None)
        get_upper = getattr(adjustment, "get_upper", None)
        if not callable(get_value) or not callable(get_page_size) or not callable(get_upper):
            return
        try:
            value = float(get_value() or 0.0)
            page_size = float(get_page_size() or 0.0)
            upper = float(get_upper() or 0.0)
        except (TypeError, ValueError):
            return
        if value + page_size >= max(0.0, upper - (page_size * 1.5)):
            self._schedule_append_next_chunk()

    def _build_card(self, item: dict[str, object]) -> Gtk.FlowBoxChild:
        item_dict = dict(item)
        button = Gtk.Button()
        button.set_has_frame(False)
        button.add_css_class("ipod-gallery-card")
        button.connect("clicked", self._handle_card_clicked, item_dict)

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        body.set_margin_top(6)
        body.set_margin_bottom(6)
        body.set_margin_start(6)
        body.set_margin_end(6)

        cover_frame = Gtk.Frame()
        cover_frame.add_css_class("ipod-gallery-cover-frame")
        cover_frame.set_halign(Gtk.Align.CENTER)
        cover_frame.set_child(
            self._build_cover_media(
                item_dict,
                size=max(_CARD_MIN_WIDTH - 16, 120),
                placeholder_caption="",
            )
        )
        body.append(cover_frame)

        title = Gtk.Label(label=str(item_dict.get("title") or "Unknown Title"))
        title.set_xalign(0.0)
        title.set_wrap(True)
        title.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        title.set_max_width_chars(26)
        title.set_lines(2)
        title.add_css_class("ipod-gallery-card-title")
        body.append(title)

        artist = str(item_dict.get("artist") or "Unknown Artist")
        year_value = item_dict.get("year")
        year_text = str(year_value).strip() if year_value is not None else ""
        subtitle_text = artist if not year_text else f"{artist} • {year_text}"
        subtitle = Gtk.Label(label=subtitle_text)
        subtitle.set_xalign(0.0)
        subtitle.set_wrap(True)
        subtitle.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        subtitle.set_max_width_chars(26)
        subtitle.set_lines(2)
        subtitle.add_css_class("ipod-gallery-card-subtitle")
        body.append(subtitle)

        button.set_child(body)
        card_child = Gtk.FlowBoxChild()
        card_child.set_child(button)

        button_id = id(button)
        self._button_to_item[button_id] = item_dict
        self._buttons_by_id[button_id] = button
        self._button_to_frame[button_id] = cover_frame
        media = cover_frame.get_child()
        if media is not None:
            self._button_to_media[button_id] = media
        release_id = item_dict.get("discogs_release_id")
        if isinstance(release_id, int):
            self._release_id_to_button[int(release_id)] = button
        return card_child

    def _handle_card_clicked(
        self,
        _button: Gtk.Button,
        item: dict[str, object],
    ) -> None:
        self._select_item(item, emit=True)

    def _selected_item(self) -> dict[str, object] | None:
        if self._selected_release_id is None:
            return None
        button = self._release_id_to_button.get(int(self._selected_release_id))
        if button is None:
            return None
        item = self._button_to_item.get(id(button))
        return dict(item) if isinstance(item, dict) else None

    def _set_card_selection(self, release_id: int | None) -> None:
        next_button_id: int | None = None
        if release_id is not None:
            selected_button = self._release_id_to_button.get(int(release_id))
            if selected_button is not None:
                next_button_id = id(selected_button)

        if self._selected_button_id == next_button_id:
            return

        if self._selected_button_id is not None:
            previous_button = self._buttons_by_id.get(self._selected_button_id)
            if previous_button is not None:
                previous_button.remove_css_class("is-selected")

        self._selected_button_id = next_button_id
        if self._selected_button_id is None:
            return

        selected_button = self._buttons_by_id.get(self._selected_button_id)
        if selected_button is not None:
            selected_button.add_css_class("is-selected")

    def _scroll_to_selected(self) -> None:
        if self._selected_button_id is None:
            return
        button = self._buttons_by_id.get(self._selected_button_id)
        if button is None:
            return
        ok, rect = button.compute_bounds(self._flow)
        if not ok:
            return
        adj = self._scroll.get_vadjustment()
        page_size = adj.get_page_size()
        current = adj.get_value()
        top = float(rect.origin.y)
        bottom = top + float(rect.size.height)
        if top < current:
            adj.set_value(max(0.0, top - 8.0))
        elif bottom > current + page_size:
            adj.set_value(min(adj.get_upper() - page_size, bottom - page_size + 8.0))

    def _select_item(self, item: dict[str, object] | None, *, emit: bool) -> None:
        if not isinstance(item, dict):
            self.clear_selection(emit=emit)
            return
        release_id = item.get("discogs_release_id")
        if not isinstance(release_id, int):
            self.clear_selection(emit=emit)
            return
        item_dict = dict(item)
        self._selected_release_id = int(release_id)
        self._set_card_selection(self._selected_release_id)
        GLib.idle_add(self._scroll_to_selected)
        if self._on_selection_changed is not None and emit:
            self._on_selection_changed(item_dict)

    def set_items(self, items: list[dict[str, object]]) -> None:
        previous_selected = self._selected_release_id
        self._items = [dict(item) for item in items]
        self._selected_release_id = None
        self._clear()
        initial_count = max(1, int(self._perf.gallery_initial_items))
        self._append_items_until(initial_count)
        if self._rendered_count < len(self._items):
            self._schedule_append_next_chunk()
        self._apply_responsive_layout()
        if isinstance(previous_selected, int):
            self.select_release(previous_selected)

    def has_active_selection(self) -> bool:
        return isinstance(self._selected_release_id, int)

    def current_columns(self) -> int:
        return max(1, int(self._columns))

    def clear_selection(self, *, emit: bool = True) -> None:
        self._selected_release_id = None
        self._set_card_selection(None)
        if self._on_selection_changed is not None and emit:
            self._on_selection_changed(None)

    def select_release(self, discogs_release_id: int) -> bool:
        if not self._ensure_release_rendered(int(discogs_release_id)):
            return False
        button = self._release_id_to_button.get(int(discogs_release_id))
        if button is None:
            return False
        item = self._button_to_item.get(id(button))
        if not isinstance(item, dict):
            return False
        self._select_item(dict(item), emit=True)
        return True

    def set_release_spotify_album_id(
        self, discogs_release_id: int, spotify_album_id: object | None
    ) -> None:
        normalized_album_id = str(spotify_album_id or "").strip()
        for item in self._items:
            if item.get("discogs_release_id") == int(discogs_release_id):
                item["spotify_album_id"] = normalized_album_id or None
                break
        button = self._release_id_to_button.get(int(discogs_release_id))
        if button is None:
            return
        button_id = id(button)
        button_item = self._button_to_item.get(button_id)
        if not isinstance(button_item, dict):
            return
        button_item["spotify_album_id"] = normalized_album_id or None
        self._button_to_item[button_id] = button_item

    def _compute_columns(self, usable_width: int) -> int:
        for candidate in range(_MAX_COLUMNS, _MIN_COLUMNS - 1, -1):
            per_card = (usable_width - (_GRID_GAP * (candidate - 1))) // candidate
            if per_card >= _CARD_MIN_WIDTH:
                return candidate
        return _MIN_COLUMNS

    def _apply_responsive_layout(self) -> None:
        width = max(self._layout_width, int(self.get_width() or 0), 1)
        height = max(self._layout_height, int(self.get_height() or 0), 1)
        usable_width = max(width - (2 * _GRID_MARGIN) - self._reserved_right_width, 360)
        usable_height = max(height - (2 * _GRID_MARGIN), 320)

        columns = self._compute_columns(usable_width)
        width_limited = (usable_width - (_GRID_GAP * (columns - 1))) // columns
        height_limited = (
            (usable_height - (_GRID_GAP * (_TARGET_VISIBLE_ROWS - 1))) // _TARGET_VISIBLE_ROWS
        ) - _CARD_TEXT_HEIGHT
        card_width = min(_CARD_MAX_WIDTH, width_limited)
        if height_limited > 0:
            card_width = min(card_width, height_limited)
        card_width = max(_CARD_MIN_WIDTH, card_width)

        cover_size = max(112, card_width - 16)
        card_height = cover_size + _CARD_TEXT_HEIGHT
        layout_changed = (
            columns != self._columns
            or card_width != self._card_width
            or cover_size != self._cover_size
        )

        self._card_width = card_width
        self._cover_size = cover_size
        if columns != self._columns:
            self._columns = int(columns)
            self._flow.set_min_children_per_line(columns)
            self._flow.set_max_children_per_line(columns)
        if layout_changed:
            for button in self._buttons_by_id.values():
                button_id = id(button)
                button.set_size_request(card_width, card_height)
                frame = self._button_to_frame.get(button_id)
                if frame is not None:
                    frame.set_size_request(cover_size, cover_size)
                media = self._button_to_media.get(button_id)
                if isinstance(media, Gtk.Picture):
                    media.set_size_request(cover_size, cover_size)

    def _schedule_responsive_layout(self) -> None:
        if self._pending_layout_source_id is not None:
            return
        self._pending_layout_source_id = GLib.timeout_add(
            _RESIZE_DEBOUNCE_MS, self._flush_pending_responsive_layout
        )

    def _flush_pending_responsive_layout(self) -> bool:
        self._pending_layout_source_id = None
        self._apply_responsive_layout()
        return False

    def _cancel_pending_responsive_layout(self) -> None:
        if self._pending_layout_source_id is None:
            return
        GLib.source_remove(self._pending_layout_source_id)
        self._pending_layout_source_id = None

    def apply_layout_hint(
        self,
        width: int,
        height: int,
        *,
        reserved_right_width: int = 0,
    ) -> None:
        self._layout_width = max(1, int(width))
        self._layout_height = max(1, int(height))
        self._reserved_right_width = max(0, int(reserved_right_width))
        self._schedule_responsive_layout()

    def _handle_size_change(self, _widget: Gtk.Widget, _param) -> None:
        self._schedule_responsive_layout()

    def _handle_destroy(self, _widget: Gtk.Widget) -> None:
        self._cancel_pending_responsive_layout()
        if self._pending_append_source_id is not None:
            GLib.source_remove(self._pending_append_source_id)
            self._pending_append_source_id = None
