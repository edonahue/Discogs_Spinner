"""Album cover carousel with previous/next browsing controls."""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


class CoverCarousel(Gtk.Box):
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

        self._cover_frame = Gtk.Frame()
        self._cover_frame.set_hexpand(True)
        self._cover_frame.set_vexpand(True)
        self._cover_frame.add_css_class("ipod-cover-frame")
        self.append(self._cover_frame)

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

    def _set_cover_widget(self, item: dict[str, object] | None) -> None:
        if not isinstance(item, dict):
            placeholder = Gtk.Label(label="No Album")
            placeholder.set_halign(Gtk.Align.CENTER)
            placeholder.set_valign(Gtk.Align.CENTER)
            placeholder.add_css_class("ipod-cover-placeholder")
            self._cover_frame.set_child(placeholder)
            return

        cover_path = str(item.get("cover_path") or "").strip()
        if cover_path:
            picture = Gtk.Picture.new_for_filename(cover_path)
            picture.set_can_shrink(True)
            picture.set_size_request(360, 360)
            picture.set_content_fit(Gtk.ContentFit.COVER)
            self._cover_frame.set_child(picture)
            return

        missing = Gtk.Image.new_from_icon_name("media-optical-symbolic")
        missing.set_pixel_size(128)
        missing.set_halign(Gtk.Align.CENTER)
        missing.set_valign(Gtk.Align.CENTER)
        self._cover_frame.set_child(missing)

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
            self._set_cover_widget(None)
            self._title.set_text("No release selected")
            self._meta.set_text("")
            self._position.set_text("0 / 0")
            if emit and self._on_selection_changed is not None:
                self._on_selection_changed(None)
            return

        item = self._items[self._index]
        self._set_cover_widget(item)
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
