"""Album cover carousel with iPod-style three-cover flow browsing."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, GLib, Gio, Gtk

from discogs_player.services.image_cache import get_or_fetch_cover_path

_CAROUSEL_PREFETCH_LOOKAHEAD = 48
_CAROUSEL_PREFETCH_BACKTRACK = 8
_CAROUSEL_PREFETCH_MAX_WORKERS = 32


class CoverCarousel(Gtk.Box):
    _CENTER_SLOT_SIZE = 420
    _SIDE_SLOT_SIZE = 210
    _CENTER_TO_SIDE_RATIO = 2.2
    _MIN_CENTER_SLOT_SIZE = 280
    _MAX_CENTER_SLOT_SIZE = 980
    _MIN_SIDE_SLOT_SIZE = 72
    _MAX_SIDE_SLOT_SIZE = 560
    _SIDE_WIDTH_MAX_RATIO_OF_CENTER = 0.95
    _SIDE_HEIGHT_MAX_RATIO_OF_CENTER = 0.92
    _COVER_STRIP_HORIZONTAL_PADDING = 12
    _COVER_STRIP_VERTICAL_OVERHEAD = 52
    _COVER_STRIP_GAP_TOTAL = 28
    _RESIZE_DEBOUNCE_MS = 40
    _MIN_LAYOUT_HINT_WIDTH = 360
    _MIN_LAYOUT_HINT_HEIGHT = 220
    _MAX_STARTUP_LAYOUT_PROBES = 20
    _CENTER_SPIN_INTERVAL_MS = 66
    _CENTER_SPIN_MIN_TICKS = 24

    def __init__(
        self,
        *,
        on_selection_changed: Callable[[dict[str, object] | None], None] | None = None,
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.set_vexpand(True)
        self.set_hexpand(True)
        self.add_css_class("ipod-carousel")
        self._on_selection_changed = on_selection_changed
        self._items: list[dict[str, object]] = []
        self._id_to_index: dict[int, int] = {}
        self._index = -1
        self._prefetch_generation = 0
        self._prefetch_inflight: set[int] = set()
        self._prefetch_executor = ThreadPoolExecutor(
            max_workers=_CAROUSEL_PREFETCH_MAX_WORKERS,
            thread_name_prefix="carousel-cover-prefetch",
        )
        self._center_spin_source_id: int | None = None
        self._center_spin_target_release_id: int | None = None
        self._center_spin_target_index: int | None = None
        self._center_spin_tick = 0
        self._center_spin_on_complete: Callable[[], None] | None = None
        self._texture_cache: dict[str, Gdk.Texture] = {}
        self._center_slot_width = int(self._CENTER_SLOT_SIZE)
        self._center_slot_height = int(self._CENTER_SLOT_SIZE)
        self._side_slot_width = int(self._SIDE_SLOT_SIZE)
        self._side_slot_height = int(self._SIDE_SLOT_SIZE)
        self._pending_resize_source_id: int | None = None
        self._pending_resize_width: int = 0
        self._pending_resize_height: int = 0
        self._startup_layout_probes_remaining = int(self._MAX_STARTUP_LAYOUT_PROBES)
        self._last_stable_hint_width: int = 0
        self._last_stable_hint_height: int = 0

        self._cover_strip = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        self._cover_strip.set_halign(Gtk.Align.CENTER)
        self._cover_strip.set_valign(Gtk.Align.CENTER)
        self._cover_strip.set_hexpand(True)
        self._cover_strip.set_vexpand(True)
        self._cover_strip.add_css_class("ipod-cover-strip")
        self.append(self._cover_strip)

        self._left_cover = self._build_cover_slot(
            width=self._SIDE_SLOT_SIZE,
            height=self._SIDE_SLOT_SIZE,
            css_class="ipod-cover-slot-side",
            step_delta=-1,
        )
        self._center_cover = self._build_cover_slot(
            width=self._CENTER_SLOT_SIZE,
            height=self._CENTER_SLOT_SIZE,
            css_class="ipod-cover-slot-center",
            step_delta=0,
        )
        self._right_cover = self._build_cover_slot(
            width=self._SIDE_SLOT_SIZE,
            height=self._SIDE_SLOT_SIZE,
            css_class="ipod-cover-slot-side",
            step_delta=1,
        )
        self._cover_strip.append(self._left_cover)
        self._cover_strip.append(self._center_cover)
        self._cover_strip.append(self._right_cover)

        # Removed title/meta label as requested

        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        controls.set_halign(Gtk.Align.START)
        self.append(controls)

        self._prev_button = Gtk.Button(label="◀ Prev")
        self._prev_button.add_css_class("pill")
        self._prev_button.connect("clicked", lambda *_: self._step(-1))
        controls.append(self._prev_button)

        self._position = Gtk.Label(label="0 / 0")
        self._position.add_css_class("ipod-carousel-meta")
        controls.append(self._position)

        self._next_button = Gtk.Button(label="Next ▶")
        self._next_button.add_css_class("pill")
        self._next_button.connect("clicked", lambda *_: self._step(1))
        controls.append(self._next_button)

        self.connect("notify::width", self._on_size_change)
        self.connect("notify::height", self._on_size_change)
        GLib.idle_add(self._apply_responsive_slot_sizes_from_current_size)

        self._render_current(emit=False)

    def do_unroot(self) -> None:  # pragma: no cover - lifecycle callback
        self._clear_center_spin_state()
        if self._pending_resize_source_id is not None:
            source_id = self._pending_resize_source_id
            self._pending_resize_source_id = None
            try:
                GLib.source_remove(source_id)
            except Exception:
                pass
        self._texture_cache.clear()
        self._prefetch_executor.shutdown(wait=False, cancel_futures=True)
        super().do_unroot()

    def _clear_center_spin_state(self, *, remove_source: bool = True) -> bool:
        was_active = self._center_spin_source_id is not None
        if remove_source and self._center_spin_source_id is not None:
            source_id = self._center_spin_source_id
            self._center_spin_source_id = None
            try:
                GLib.source_remove(source_id)
            except Exception:
                pass
        else:
            self._center_spin_source_id = None
        self._center_spin_target_release_id = None
        self._center_spin_target_index = None
        self._center_spin_tick = 0
        self._center_spin_on_complete = None
        return was_active

    def _current_center_item(self) -> dict[str, object] | None:
        if not self._items or self._index < 0:
            return None
        item = self._items[self._index]
        return item if isinstance(item, dict) else None

    def _set_center_spin_target_index(self, discogs_release_id: int | None) -> None:
        self._center_spin_target_release_id = (
            int(discogs_release_id) if discogs_release_id else None
        )
        if self._center_spin_target_release_id is None:
            self._center_spin_target_index = None
            return
        self._center_spin_target_index = self._id_to_index.get(
            self._center_spin_target_release_id
        )
        if self._center_spin_target_index is None or not self._items:
            return
        self._queue_cover_prefetch(self._center_spin_target_index)
        if len(self._items) > 1:
            self._queue_cover_prefetch(
                (self._center_spin_target_index - 1) % len(self._items)
            )
            self._queue_cover_prefetch(
                (self._center_spin_target_index + 1) % len(self._items)
            )

    def set_spin_target_release(self, discogs_release_id: int | None) -> None:
        self._set_center_spin_target_index(discogs_release_id)

    @staticmethod
    def _spin_stride_for_remaining(remaining: int) -> int:
        if remaining > 48:
            return 7
        if remaining > 28:
            return 5
        if remaining > 14:
            return 3
        if remaining > 7:
            return 2
        return 1

    def _advance_center_spin_animation(self) -> bool:
        try:
            return self._inner_advance_center_spin_animation()
        except Exception:
            import traceback
            traceback.print_exc()
            callback = self._center_spin_on_complete
            self._clear_center_spin_state(remove_source=False)
            if callback:
                GLib.idle_add(callback)
            return False

    def _inner_advance_center_spin_animation(self) -> bool:
        if not self._items or self._index < 0:
            callback = self._center_spin_on_complete
            self._clear_center_spin_state(remove_source=False)
            if callback:
                GLib.idle_add(callback)
            return False
        count = len(self._items)
        if count < 2:
            callback = self._center_spin_on_complete
            self._clear_center_spin_state(remove_source=False)
            if callback:
                GLib.idle_add(callback)
            return False
        self._center_spin_tick += 1

        target_index = self._center_spin_target_index
        if target_index is None or self._center_spin_tick < self._CENTER_SPIN_MIN_TICKS:
            delta = 1
        else:
            forward = (target_index - self._index) % count
            backward = (self._index - target_index) % count
            if forward == 0:
                callback = self._center_spin_on_complete
                self._clear_center_spin_state(remove_source=False)
                if callback:
                    # Run callback in idle to avoid reentrancy
                    GLib.idle_add(callback)
                return False
            if forward <= backward:
                direction = 1
                remaining = forward
            else:
                direction = -1
                remaining = backward
            delta = direction * min(
                self._spin_stride_for_remaining(remaining), remaining
            )

        next_index = (self._index + delta) % count
        self._index = next_index
        self._render_current(emit=False)
        return True

    def start_center_spin_animation(self, *, on_complete: Callable[[], None] | None = None) -> None:
        self._clear_center_spin_state()
        if not self._items or self._index < 0 or len(self._items) < 2:
            if on_complete:
                on_complete()
            return

        self._center_spin_tick = 0
        self._center_spin_on_complete = on_complete
        self._set_center_spin_target_index(None)
        self._queue_cover_prefetch(self._index)
        self._prefetch_covers_near_index()
        self._center_spin_source_id = GLib.timeout_add(
            self._CENTER_SPIN_INTERVAL_MS,
            self._advance_center_spin_animation,
        )

    def stop_center_spin_animation(self, *, invoke_callback: bool = False) -> None:
        callback = self._center_spin_on_complete if invoke_callback else None
        was_active = self._clear_center_spin_state()
        if was_active:
            self._render_current(emit=False)
        if callback:
            GLib.idle_add(callback)

    def _build_cover_slot(
        self, *, width: int, height: int, css_class: str, step_delta: int
    ) -> Gtk.Frame:
        frame = Gtk.Frame()
        frame.set_size_request(width, height)
        frame.set_hexpand(False)
        frame.set_vexpand(False)
        frame.set_halign(Gtk.Align.CENTER)
        frame.set_valign(Gtk.Align.CENTER)
        frame.add_css_class("ipod-cover-frame")
        frame.add_css_class("ipod-cover-slot")
        frame.add_css_class(css_class)
        if step_delta:
            click = Gtk.GestureClick.new()
            click.connect("released", lambda *_: self._step(step_delta))
            frame.add_controller(click)
        return frame

    def _build_cover_placeholder(self, caption: str, *, icon_size: int) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_halign(Gtk.Align.CENTER)
        box.set_valign(Gtk.Align.CENTER)

        icon = Gtk.Image.new_from_icon_name("media-record-symbolic")
        if icon.get_paintable() is None:
            icon = Gtk.Image.new_from_icon_name("media-optical-symbolic")
        icon.set_pixel_size(icon_size)
        icon.set_halign(Gtk.Align.CENTER)
        icon.set_valign(Gtk.Align.CENTER)
        icon.add_css_class("ipod-cover-placeholder")
        box.append(icon)

        label = Gtk.Label(label=caption)
        label.set_halign(Gtk.Align.CENTER)
        label.add_css_class("ipod-cover-placeholder")
        box.append(label)
        return box

    def _get_cached_texture(self, cover_path: str) -> Gdk.Texture | None:
        texture = self._texture_cache.get(cover_path)
        if texture is not None:
            return texture
        try:
            gfile = Gio.File.new_for_path(cover_path)
            texture = Gdk.Texture.new_from_file(gfile)
        except Exception:
            return None
        self._texture_cache[cover_path] = texture
        return texture

    def _build_cover_widget(
        self,
        item: dict[str, object] | None,
        *,
        width: int,
        height: int,
        placeholder_caption: str,
    ) -> Gtk.Widget:
        if isinstance(item, dict):
            cover_path = str(item.get("cover_path") or "").strip()
            if cover_path:
                texture = self._get_cached_texture(cover_path)
                if texture is not None:
                    picture = Gtk.Picture.new_for_paintable(texture)
                else:
                    picture = Gtk.Picture.new_for_filename(cover_path)
                picture.set_can_shrink(True)
                picture.set_size_request(width, height)
                picture.set_content_fit(Gtk.ContentFit.COVER)
                return picture
        icon_size = max(56, int(min(width, height) * 0.24))
        return self._build_cover_placeholder(placeholder_caption, icon_size=icon_size)

    def _set_slot_cover(
        self,
        frame: Gtk.Frame,
        *,
        item: dict[str, object] | None,
        width: int,
        height: int,
        placeholder_caption: str,
    ) -> None:
        frame.set_child(
            self._build_cover_widget(
                item,
                width=width,
                height=height,
                placeholder_caption=placeholder_caption,
            )
        )

    def _compute_responsive_slot_sizes(
        self, width: int, height: int
    ) -> tuple[int, int, int, int]:
        usable_width = max(int(width) - self._COVER_STRIP_HORIZONTAL_PADDING, 1)
        usable_height = max(int(height) - self._COVER_STRIP_VERTICAL_OVERHEAD, 1)
        min_side_width = int(self._MIN_SIDE_SLOT_SIZE)
        gap = int(self._COVER_STRIP_GAP_TOTAL)
        center_max_by_height = max(1, min(int(self._MAX_CENTER_SLOT_SIZE), usable_height))

        center_square_target = max(1, usable_width - gap - (2 * min_side_width))
        center_height = min(center_max_by_height, center_square_target)
        center_height = max(
            min(int(self._MIN_CENTER_SLOT_SIZE), center_max_by_height),
            center_height,
        )
        center_height = max(140, center_height)
        center_width_min = max(140, int(round(center_height * 0.97)))
        center_width_max = max(center_width_min, int(round(center_height * 1.03)))

        max_center_width_from_layout = max(1, usable_width - gap - (2 * min_side_width))
        center_width = min(
            center_width_max,
            max(center_width_min, max_center_width_from_layout),
        )
        if center_width < center_width_min:
            center_width = max(140, center_width)

        remaining = usable_width - gap - center_width
        if remaining < (2 * min_side_width):
            center_width = max(140, usable_width - gap - (2 * min_side_width))
            remaining = usable_width - gap - center_width
        side_width = max(min_side_width, remaining // 2)
        side_width = min(
            side_width,
            int(self._MAX_SIDE_SLOT_SIZE),
            max(min_side_width, int(round(center_width * self._SIDE_WIDTH_MAX_RATIO_OF_CENTER))),
        )

        side_height = int(round(center_height * 0.86))
        side_height = min(
            int(self._MAX_SIDE_SLOT_SIZE),
            max(56, side_height),
            max(56, int(round(center_height * self._SIDE_HEIGHT_MAX_RATIO_OF_CENTER))),
        )

        return (
            int(center_width),
            int(center_height),
            int(side_width),
            int(side_height),
        )

    def _apply_responsive_slot_sizes(self, width: int, height: int) -> None:
        (
            center_width,
            center_height,
            side_width,
            side_height,
        ) = self._compute_responsive_slot_sizes(width, height)
        if (
            center_width == self._center_slot_width
            and center_height == self._center_slot_height
            and side_width == self._side_slot_width
            and side_height == self._side_slot_height
        ):
            return

        self._center_slot_width = center_width
        self._center_slot_height = center_height
        self._side_slot_width = side_width
        self._side_slot_height = side_height
        self._center_cover.set_size_request(center_width, center_height)
        self._left_cover.set_size_request(side_width, side_height)
        self._right_cover.set_size_request(side_width, side_height)
        self._render_current(emit=False)

    def _schedule_responsive_slot_update(self, width: int, height: int) -> None:
        coerced_width, coerced_height = self._coerce_layout_hint_dimensions(width, height)
        self._pending_resize_width = coerced_width
        self._pending_resize_height = coerced_height
        if self._pending_resize_source_id is not None:
            return
        self._pending_resize_source_id = GLib.timeout_add(
            self._RESIZE_DEBOUNCE_MS,
            self._flush_pending_responsive_slot_update,
        )

    def _flush_pending_responsive_slot_update(self) -> bool:
        self._pending_resize_source_id = None
        self._apply_responsive_slot_sizes(
            self._pending_resize_width,
            self._pending_resize_height,
        )
        return False

    def _effective_resize_dimensions(self, widget: Gtk.Widget) -> tuple[int, int]:
        width = max(1, int(widget.get_width() or 0))
        height = max(1, int(widget.get_height() or 0))
        current = widget.get_parent()
        hops = 0
        while current is not None and hops < 12:
            width = max(width, int(current.get_width() or 0))
            height = max(height, int(current.get_height() or 0))
            current = current.get_parent()
            hops += 1
        return width, height

    def _coerce_layout_hint_dimensions(self, width: int, height: int) -> tuple[int, int]:
        candidate_width = max(1, int(width))
        candidate_height = max(1, int(height))

        # Trust explicit real viewport hints; avoid over-inflating after snap/restore.
        if (
            candidate_width >= self._MIN_LAYOUT_HINT_WIDTH
            and candidate_height >= self._MIN_LAYOUT_HINT_HEIGHT
        ):
            self._last_stable_hint_width = candidate_width
            self._last_stable_hint_height = candidate_height
            return candidate_width, candidate_height

        local_width, local_height = self._effective_resize_dimensions(self)
        candidate_width = max(candidate_width, local_width)
        candidate_height = max(candidate_height, local_height)

        root = self.get_root()
        if root is not None:
            try:
                root_width = int(root.get_width() or 0)
                root_height = int(root.get_height() or 0)
            except Exception:
                root_width = 0
                root_height = 0
            if root_width > 1:
                candidate_width = max(candidate_width, int(root_width * 0.55))
            if root_height > 1:
                candidate_height = max(candidate_height, int(root_height * 0.45))

        # Avoid regressing to tiny dimensions after we already observed a stable layout.
        if (
            candidate_width < self._MIN_LAYOUT_HINT_WIDTH
            or candidate_height < self._MIN_LAYOUT_HINT_HEIGHT
        ) and (
            self._last_stable_hint_width >= self._MIN_LAYOUT_HINT_WIDTH
            and self._last_stable_hint_height >= self._MIN_LAYOUT_HINT_HEIGHT
        ):
            candidate_width = max(candidate_width, self._last_stable_hint_width)
            candidate_height = max(candidate_height, self._last_stable_hint_height)

        # Keep current slot footprint as a floor when hints are noisy.
        current_slot_width = (
            int(self._center_slot_width)
            + (2 * int(self._side_slot_width))
            + int(self._COVER_STRIP_GAP_TOTAL)
            + int(self._COVER_STRIP_HORIZONTAL_PADDING)
        )
        current_slot_height = int(self._center_slot_height) + int(
            self._COVER_STRIP_VERTICAL_OVERHEAD
        )
        candidate_width = max(candidate_width, current_slot_width)
        candidate_height = max(candidate_height, current_slot_height)

        if (
            candidate_width >= self._MIN_LAYOUT_HINT_WIDTH
            and candidate_height >= self._MIN_LAYOUT_HINT_HEIGHT
        ):
            self._last_stable_hint_width = candidate_width
            self._last_stable_hint_height = candidate_height

        return candidate_width, candidate_height

    def apply_layout_hint(self, width: int, height: int) -> None:
        self._schedule_responsive_slot_update(width, height)

    def _on_size_change(self, widget: Gtk.Widget, _param) -> None:
        width, height = self._effective_resize_dimensions(widget)
        self._schedule_responsive_slot_update(width, height)

    def _apply_responsive_slot_sizes_from_current_size(self) -> bool:
        width, height = self._effective_resize_dimensions(self)
        if (
            width < self._MIN_LAYOUT_HINT_WIDTH
            or height < self._MIN_LAYOUT_HINT_HEIGHT
        ) and self._startup_layout_probes_remaining > 0:
            self._startup_layout_probes_remaining -= 1
            GLib.timeout_add(60, self._apply_responsive_slot_sizes_from_current_size)
            return False
        self._apply_responsive_slot_sizes(width, height)
        return False

    def _slot_indices(self) -> tuple[int | None, int | None, int | None]:
        if not self._items or self._index < 0:
            return (None, None, None)

        count = len(self._items)
        center = self._index
        if count == 1:
            return (None, center, None)

        left = (center - 1) % count
        right = (center + 1) % count
        right_index: int | None = right
        if left == right:
            right_index = None
        return (left, center, right_index)

    def _visible_indices(self) -> set[int]:
        return {index for index in self._slot_indices() if isinstance(index, int)}

    def _prefetch_cover_worker(
        self,
        *,
        discogs_release_id: int,
        cover_url: str,
        generation: int,
    ) -> None:
        try:
            cover_path = get_or_fetch_cover_path(cover_url)
        except Exception:
            cover_path = None
        GLib.idle_add(
            self._complete_cover_prefetch,
            discogs_release_id,
            generation,
            cover_path,
        )

    def _complete_cover_prefetch(
        self,
        discogs_release_id: int,
        generation: int,
        cover_path: str | None,
    ) -> bool:
        self._prefetch_inflight.discard(int(discogs_release_id))
        if generation != self._prefetch_generation:
            return False

        index = self._id_to_index.get(int(discogs_release_id))
        if index is None or not cover_path:
            return False

        item = self._items[index]
        if not str(item.get("cover_path") or "").strip():
            item["cover_path"] = cover_path
            # Eagerly warm the texture cache so the spin animation
            # doesn't have to decode JPEGs on its tight timer tick.
            self._get_cached_texture(cover_path)
            if index in self._visible_indices():
                self._render_current(emit=False)
        return False

    def _queue_cover_prefetch(self, index: int) -> None:
        release_id_obj = self._items[index].get("discogs_release_id")
        if not isinstance(release_id_obj, int):
            return

        discogs_release_id: int = release_id_obj
        if discogs_release_id in self._prefetch_inflight:
            return

        self._prefetch_inflight.add(discogs_release_id)
        generation = self._prefetch_generation
        cover_url_obj = self._items[index].get("cover_url")
        cover_url = str(cover_url_obj or "")

        try:
            self._prefetch_executor.submit(
                self._prefetch_cover_worker,
                discogs_release_id=discogs_release_id,
                cover_url=cover_url,
                generation=generation,
            )
        except RuntimeError:
            self._prefetch_inflight.discard(discogs_release_id)

    def _prefetch_covers_near_index(self) -> None:
        if not self._items or self._index < 0:
            return

        count = len(self._items)
        priority: list[int] = []
        left, center, right = self._slot_indices()
        for slot_index in (left, center, right):
            if isinstance(slot_index, int):
                priority.append(slot_index)

        for offset in range(2, _CAROUSEL_PREFETCH_LOOKAHEAD + 1):
            priority.append((self._index + offset) % count)
        for offset in range(2, _CAROUSEL_PREFETCH_BACKTRACK + 1):
            priority.append((self._index - offset) % count)

        seen: set[int] = set()
        for candidate_index in priority:
            if candidate_index in seen:
                continue
            seen.add(candidate_index)
            self._queue_cover_prefetch(candidate_index)

    def _step(self, delta: int) -> None:
        if not self._items:
            return
        next_index = (self._index + int(delta)) % len(self._items)
        self._set_index(next_index, emit=True)

    def _set_index(self, index: int, *, emit: bool) -> None:
        if not self._items:
            self._clear_center_spin_state()
            self._index = -1
            self._render_current(emit=emit)
            return

        clamped = max(0, min(int(index), len(self._items) - 1))
        if self._index != clamped:
            self._clear_center_spin_state()
        self._index = clamped
        self._render_current(emit=emit)

    def _render_current(self, *, emit: bool) -> None:
        has_items = bool(self._items)
        self._prev_button.set_sensitive(has_items and len(self._items) > 1)
        self._next_button.set_sensitive(has_items and len(self._items) > 1)

        if not has_items or self._index < 0:
            self._set_slot_cover(
                self._left_cover,
                item=None,
                width=self._side_slot_width,
                height=self._side_slot_height,
                placeholder_caption="",
            )
            self._set_slot_cover(
                self._center_cover,
                item=None,
                width=self._center_slot_width,
                height=self._center_slot_height,
                placeholder_caption="No release selected",
            )
            self._set_slot_cover(
                self._right_cover,
                item=None,
                width=self._side_slot_width,
                height=self._side_slot_height,
                placeholder_caption="",
            )
            self._position.set_text("0 / 0")
            if emit and self._on_selection_changed is not None:
                self._on_selection_changed(None)
            return

        left_index, center_index, right_index = self._slot_indices()
        left_item = self._items[left_index] if isinstance(left_index, int) else None
        center_item = self._items[center_index] if isinstance(center_index, int) else None
        right_item = self._items[right_index] if isinstance(right_index, int) else None

        self._set_slot_cover(
            self._left_cover,
            item=left_item,
            width=self._side_slot_width,
            height=self._side_slot_height,
            placeholder_caption="",
        )
        self._set_slot_cover(
            self._center_cover,
            item=center_item,
            width=self._center_slot_width,
            height=self._center_slot_height,
            placeholder_caption="No release selected",
        )
        self._set_slot_cover(
            self._right_cover,
            item=right_item,
            width=self._side_slot_width,
            height=self._side_slot_height,
            placeholder_caption="",
        )

        self._position.set_text(f"{self._index + 1} / {len(self._items)}")
        if emit and self._on_selection_changed is not None:
            self._on_selection_changed(center_item)
        return

    def set_items(self, items: list[dict[str, object]]) -> None:
        self._clear_center_spin_state()
        self._prefetch_generation += 1
        self._prefetch_inflight.clear()
        self._items = [dict(item) for item in items]
        self._id_to_index.clear()
        for index, item in enumerate(self._items):
            release_id = item.get("discogs_release_id")
            if isinstance(release_id, int):
                self._id_to_index[release_id] = index

        self._set_index(0 if self._items else -1, emit=True)

    def select_release(self, discogs_release_id: int) -> bool:
        index = self._id_to_index.get(int(discogs_release_id))
        if index is None:
            return False
        self._set_index(index, emit=True)
        return True
