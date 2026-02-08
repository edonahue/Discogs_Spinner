"""Album cover carousel with iPod-style three-cover flow browsing."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk

from discogs_player.services.image_cache import get_or_fetch_cover_path

_CAROUSEL_PREFETCH_LOOKAHEAD = 24
_CAROUSEL_PREFETCH_BACKTRACK = 8
_CAROUSEL_PREFETCH_MAX_WORKERS = 16


class CoverCarousel(Gtk.Box):
    _CENTER_SLOT_SIZE = 360
    _SIDE_SLOT_SIZE = 220

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

        self._cover_strip = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        self._cover_strip.set_halign(Gtk.Align.CENTER)
        self._cover_strip.set_hexpand(True)
        self._cover_strip.set_vexpand(True)
        self._cover_strip.add_css_class("ipod-cover-strip")
        self.append(self._cover_strip)

        self._left_cover = self._build_cover_slot(
            size=self._SIDE_SLOT_SIZE,
            css_class="ipod-cover-slot-side",
            step_delta=-1,
        )
        self._center_cover = self._build_cover_slot(
            size=self._CENTER_SLOT_SIZE,
            css_class="ipod-cover-slot-center",
            step_delta=0,
        )
        self._right_cover = self._build_cover_slot(
            size=self._SIDE_SLOT_SIZE,
            css_class="ipod-cover-slot-side",
            step_delta=1,
        )
        self._cover_strip.append(self._left_cover)
        self._cover_strip.append(self._center_cover)
        self._cover_strip.append(self._right_cover)

        self._title = Gtk.Label(label="No release selected")
        self._title.set_xalign(0.5)
        self._title.add_css_class("ipod-carousel-title")
        self._title.set_wrap(True)
        self.append(self._title)

        self._meta = Gtk.Label(label="")
        self._meta.set_xalign(0.5)
        self._meta.add_css_class("ipod-carousel-meta")
        self._meta.set_wrap(True)
        self.append(self._meta)

        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        controls.set_halign(Gtk.Align.CENTER)
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

        self._render_current(emit=False)

    def do_unroot(self) -> None:  # pragma: no cover - lifecycle callback
        self._prefetch_executor.shutdown(wait=False, cancel_futures=True)
        super().do_unroot()

    def _build_cover_slot(self, *, size: int, css_class: str, step_delta: int) -> Gtk.Frame:
        frame = Gtk.Frame()
        frame.set_size_request(size, size)
        frame.set_hexpand(False)
        frame.set_vexpand(True)
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

    def _build_cover_widget(
        self,
        item: dict[str, object] | None,
        *,
        size: int,
        placeholder_caption: str,
    ) -> Gtk.Widget:
        if isinstance(item, dict):
            cover_path = str(item.get("cover_path") or "").strip()
            if cover_path:
                picture = Gtk.Picture.new_for_filename(cover_path)
                picture.set_can_shrink(True)
                picture.set_size_request(size, size)
                picture.set_content_fit(Gtk.ContentFit.COVER)
                return picture
        icon_size = 96 if size >= self._CENTER_SLOT_SIZE else 72
        return self._build_cover_placeholder(placeholder_caption, icon_size=icon_size)

    def _set_slot_cover(
        self,
        frame: Gtk.Frame,
        *,
        item: dict[str, object] | None,
        size: int,
        placeholder_caption: str,
    ) -> None:
        frame.set_child(
            self._build_cover_widget(
                item,
                size=size,
                placeholder_caption=placeholder_caption,
            )
        )

    def _slot_indices(self) -> tuple[int | None, int | None, int | None]:
        if not self._items or self._index < 0:
            return (None, None, None)

        count = len(self._items)
        center = self._index
        if count == 1:
            return (None, center, None)

        left = (center - 1) % count
        right = (center + 1) % count
        if left == right:
            right = None
        return (left, center, right)

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
            if index in self._visible_indices():
                self._render_current(emit=False)
        return False

    def _queue_cover_prefetch(self, index: int) -> None:
        if index < 0 or index >= len(self._items):
            return

        item = self._items[index]
        discogs_release_id = item.get("discogs_release_id")
        if not isinstance(discogs_release_id, int):
            return
        if discogs_release_id in self._prefetch_inflight:
            return

        if str(item.get("cover_path") or "").strip():
            return

        cover_url = str(item.get("cover_url") or "").strip()
        if not cover_url:
            return

        self._prefetch_inflight.add(discogs_release_id)
        generation = self._prefetch_generation
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
            self._index = -1
            self._render_current(emit=emit)
            return

        clamped = max(0, min(int(index), len(self._items) - 1))
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
                size=self._SIDE_SLOT_SIZE,
                placeholder_caption="",
            )
            self._set_slot_cover(
                self._center_cover,
                item=None,
                size=self._CENTER_SLOT_SIZE,
                placeholder_caption="No release selected",
            )
            self._set_slot_cover(
                self._right_cover,
                item=None,
                size=self._SIDE_SLOT_SIZE,
                placeholder_caption="",
            )
            self._title.set_text("No release selected")
            self._meta.set_text("")
            self._position.set_text("0 / 0")
            if emit and self._on_selection_changed is not None:
                self._on_selection_changed(None)
            return

        left_index, center_index, right_index = self._slot_indices()
        left_item = self._items[left_index] if isinstance(left_index, int) else None
        center_item = self._items[center_index] if isinstance(center_index, int) else None
        right_item = self._items[right_index] if isinstance(right_index, int) else None

        self._prefetch_covers_near_index()
        self._set_slot_cover(
            self._left_cover,
            item=left_item,
            size=self._SIDE_SLOT_SIZE,
            placeholder_caption="",
        )
        self._set_slot_cover(
            self._center_cover,
            item=center_item,
            size=self._CENTER_SLOT_SIZE,
            placeholder_caption="No Discogs cover",
        )
        self._set_slot_cover(
            self._right_cover,
            item=right_item,
            size=self._SIDE_SLOT_SIZE,
            placeholder_caption="",
        )

        item = center_item or {}
        artist = str(item.get("artist") or "Unknown Artist")
        title = str(item.get("title") or "Unknown Title")
        year = item.get("year")
        genres = item.get("genres")
        genre_text = ""
        if isinstance(genres, list) and genres:
            genre_text = str(genres[0] or "").strip()

        self._title.set_text(f"{artist} - {title}")
        meta_parts = [piece for piece in (str(year) if year is not None else "", genre_text) if piece]
        self._meta.set_text(" • ".join(meta_parts))
        self._position.set_text(f"{self._index + 1} / {len(self._items)}")

        if emit and self._on_selection_changed is not None:
            self._on_selection_changed(dict(item))

    def set_items(self, items: list[dict[str, object]]) -> None:
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
