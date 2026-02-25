"""Gallery cover-grid widget used by browse and wantlist sections."""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk, Pango

_GRID_GAP = 12
_GRID_MARGIN = 12
_TARGET_VISIBLE_ROWS = 3
_MIN_COLUMNS = 3
_MAX_COLUMNS = 8
_CARD_MIN_WIDTH = 148
_CARD_MAX_WIDTH = 312
_CARD_TEXT_HEIGHT = 74
_HERO_MIN_COVER_SIZE = 260
_HERO_MAX_COVER_SIZE = 760
_RESIZE_DEBOUNCE_MS = 36
_SPOTIFY_HOME_URL = "https://open.spotify.com"


def _discogs_release_url(release_id_value: object | None) -> str | None:
    if not isinstance(release_id_value, int):
        return None
    if release_id_value <= 0:
        return None
    return f"https://www.discogs.com/release/{release_id_value}"


def _discogs_marketplace_url(release_id_value: object | None) -> str | None:
    if not isinstance(release_id_value, int):
        return None
    if release_id_value <= 0:
        return None
    return f"https://www.discogs.com/sell/release/{release_id_value}"


def _spotify_album_url(album_id_value: object | None) -> str | None:
    raw = str(album_id_value or "").strip()
    if not raw:
        return None
    if raw.startswith("https://open.spotify.com/album/"):
        return raw
    if raw.startswith("http://open.spotify.com/album/"):
        return f"https://{raw.removeprefix('http://')}"
    if raw.startswith("spotify:album:"):
        normalized = raw.removeprefix("spotify:album:").strip()
        if not normalized:
            return None
        return f"https://open.spotify.com/album/{normalized}"
    if "://" in raw:
        return None
    if any(char.isspace() for char in raw):
        return None
    return f"https://open.spotify.com/album/{raw}"


class CoverGrid(Gtk.Box):
    def __init__(
        self,
        *,
        on_selection_changed: Callable[[dict[str, object] | None], None] | None = None,
        on_back_requested: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_vexpand(True)
        self.set_hexpand(True)
        self.add_css_class("ipod-gallery")
        self._on_selection_changed = on_selection_changed
        self._on_back_requested = on_back_requested

        self._items: list[dict[str, object]] = []
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
        self._hero_cover_size = _HERO_MIN_COVER_SIZE
        self._hero_media_key: tuple[int | None, str, int] | None = None
        self._pending_layout_source_id: int | None = None

        self._overlay = Gtk.Overlay()
        self._overlay.set_hexpand(True)
        self._overlay.set_vexpand(True)
        self.append(self._overlay)

        self._scroll = Gtk.ScrolledWindow()
        self._scroll.set_hexpand(True)
        self._scroll.set_vexpand(True)
        self._scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self._overlay.set_child(self._scroll)

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

        self._hero_revealer = Gtk.Revealer()
        self._hero_revealer.set_transition_type(Gtk.RevealerTransitionType.CROSSFADE)
        self._hero_revealer.set_transition_duration(170)
        self._hero_revealer.set_hexpand(True)
        self._hero_revealer.set_vexpand(True)
        self._hero_revealer.set_halign(Gtk.Align.FILL)
        self._hero_revealer.set_valign(Gtk.Align.FILL)
        self._overlay.add_overlay(self._hero_revealer)

        hero_scrim = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        hero_scrim.set_hexpand(True)
        hero_scrim.set_vexpand(True)
        hero_scrim.set_halign(Gtk.Align.FILL)
        hero_scrim.set_valign(Gtk.Align.FILL)
        hero_scrim.add_css_class("ipod-gallery-hero-scrim")
        self._hero_revealer.set_child(hero_scrim)

        hero_shell = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        hero_shell.set_halign(Gtk.Align.CENTER)
        hero_shell.set_valign(Gtk.Align.CENTER)
        hero_shell.set_margin_top(18)
        hero_shell.set_margin_bottom(18)
        hero_shell.set_margin_start(18)
        hero_shell.set_margin_end(18)
        hero_shell.add_css_class("ipod-gallery-hero-shell")
        hero_scrim.append(hero_shell)

        self._back_button = Gtk.Button(label="Back to Gallery")
        self._back_button.add_css_class("interactive-back-button")
        self._back_button.add_css_class("ipod-gallery-back-button")
        self._back_button.connect("clicked", self._handle_back_clicked)
        hero_shell.append(self._back_button)

        self._hero_frame = Gtk.Frame()
        self._hero_frame.set_halign(Gtk.Align.CENTER)
        self._hero_frame.add_css_class("ipod-gallery-hero-frame")
        hero_shell.append(self._hero_frame)

        self._hero_title = Gtk.Label(label="")
        self._hero_title.set_xalign(0.5)
        self._hero_title.set_halign(Gtk.Align.CENTER)
        self._hero_title.set_wrap(True)
        self._hero_title.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self._hero_title.set_max_width_chars(54)
        self._hero_title.add_css_class("ipod-gallery-hero-title")
        hero_shell.append(self._hero_title)

        self._hero_subtitle = Gtk.Label(label="")
        self._hero_subtitle.set_xalign(0.5)
        self._hero_subtitle.set_halign(Gtk.Align.CENTER)
        self._hero_subtitle.set_wrap(True)
        self._hero_subtitle.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self._hero_subtitle.set_max_width_chars(54)
        self._hero_subtitle.add_css_class("ipod-gallery-hero-subtitle")
        hero_shell.append(self._hero_subtitle)

        self._hero_actions_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._hero_actions_row.set_halign(Gtk.Align.CENTER)
        self._hero_actions_row.set_valign(Gtk.Align.CENTER)
        self._hero_actions_row.add_css_class("ipod-gallery-hero-actions")
        hero_shell.append(self._hero_actions_row)

        self._hero_discogs_link = Gtk.LinkButton.new("https://www.discogs.com")
        self._hero_discogs_link.set_label("Discogs Release")
        self._hero_discogs_link.add_css_class("ipod-gallery-hero-action")
        self._hero_actions_row.append(self._hero_discogs_link)

        self._hero_marketplace_link = Gtk.LinkButton.new("https://www.discogs.com")
        self._hero_marketplace_link.set_label("Marketplace")
        self._hero_marketplace_link.add_css_class("ipod-gallery-hero-action")
        self._hero_actions_row.append(self._hero_marketplace_link)

        self._hero_spotify_link = Gtk.LinkButton.new(_SPOTIFY_HOME_URL)
        self._hero_spotify_link.set_label("Spotify Album")
        self._hero_spotify_link.add_css_class("ipod-gallery-hero-action")
        self._hero_actions_row.append(self._hero_spotify_link)
        self._hero_actions_row.set_visible(False)

        self._hero_revealer.set_reveal_child(False)
        self.connect("notify::width", self._handle_size_change)
        self.connect("notify::height", self._handle_size_change)
        self.connect("destroy", self._handle_destroy)
        self._apply_responsive_layout()

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
        cover_path = str(item.get("cover_path") or "").strip()
        if cover_path:
            picture = Gtk.Picture.new_for_filename(cover_path)
            picture.set_can_shrink(True)
            picture.set_content_fit(Gtk.ContentFit.COVER)
            picture.set_size_request(size, size)
            return picture
        icon_size = max(48, int(size * 0.24))
        return self._build_placeholder(icon_size=icon_size, caption=placeholder_caption)

    def _clear(self) -> None:
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
        self._hero_media_key = None

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

    def _hero_key_for_item(self, item: dict[str, object]) -> tuple[int | None, str, int]:
        release_id = item.get("discogs_release_id")
        normalized_release_id = int(release_id) if isinstance(release_id, int) else None
        cover_path = str(item.get("cover_path") or "").strip()
        return (normalized_release_id, cover_path, int(self._hero_cover_size))

    def _update_hero_content(self, item: dict[str, object] | None) -> None:
        if not isinstance(item, dict):
            self._hero_title.set_text("")
            self._hero_subtitle.set_text("")
            self._hero_frame.set_child(None)
            self._set_hero_links(None)
            self._hero_media_key = None
            return

        title = str(item.get("title") or "Unknown Title")
        artist = str(item.get("artist") or "Unknown Artist")
        year_value = item.get("year")
        year_text = str(year_value).strip() if year_value is not None else ""
        subtitle = artist if not year_text else f"{artist} • {year_text}"
        self._hero_title.set_text(title)
        self._hero_subtitle.set_text(subtitle)
        next_key = self._hero_key_for_item(item)
        if next_key != self._hero_media_key:
            self._hero_frame.set_child(
                self._build_cover_media(
                    item,
                    size=self._hero_cover_size,
                    placeholder_caption="No Cover",
                )
            )
            self._hero_media_key = next_key
        self._set_hero_links(item)

    def _set_link_button_uri(
        self,
        button: Gtk.LinkButton,
        *,
        uri: str | None,
        label_when_available: str,
    ) -> None:
        if not uri:
            button.set_uri("https://www.discogs.com")
            button.set_sensitive(False)
            button.set_visible(False)
            return
        button.set_uri(uri)
        button.set_label(label_when_available)
        button.set_sensitive(True)
        button.set_visible(True)

    def _set_hero_links(self, item: dict[str, object] | None) -> None:
        if not isinstance(item, dict):
            self._hero_actions_row.set_visible(False)
            self._hero_discogs_link.set_visible(False)
            self._hero_marketplace_link.set_visible(False)
            self._hero_spotify_link.set_visible(False)
            return

        release_id = item.get("discogs_release_id")
        discogs_url = _discogs_release_url(release_id)
        market_url = _discogs_marketplace_url(release_id)
        spotify_url = _spotify_album_url(item.get("spotify_album_id"))

        label_suffix = (
            f" #{release_id}" if isinstance(release_id, int) and release_id > 0 else ""
        )
        self._set_link_button_uri(
            self._hero_discogs_link,
            uri=discogs_url,
            label_when_available=f"Discogs{label_suffix}",
        )
        self._set_link_button_uri(
            self._hero_marketplace_link,
            uri=market_url,
            label_when_available="Marketplace",
        )
        self._set_link_button_uri(
            self._hero_spotify_link,
            uri=spotify_url,
            label_when_available="Spotify Album",
        )
        self._hero_actions_row.set_visible(
            bool(
                self._hero_discogs_link.get_visible()
                or self._hero_marketplace_link.get_visible()
                or self._hero_spotify_link.get_visible()
            )
        )

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
        self._update_hero_content(item_dict)
        self._hero_revealer.set_reveal_child(True)
        if self._on_selection_changed is not None and emit:
            self._on_selection_changed(item_dict)

    def _handle_back_clicked(self, _button: Gtk.Button) -> None:
        self.clear_selection()
        if self._on_back_requested is not None:
            self._on_back_requested()

    def set_items(self, items: list[dict[str, object]]) -> None:
        previous_selected = self._selected_release_id
        self._items = [dict(item) for item in items]
        self._selected_release_id = None
        self._hero_revealer.set_reveal_child(False)
        self._clear()
        for item in self._items:
            self._flow.append(self._build_card(item))
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
        self._hero_revealer.set_reveal_child(False)
        self._update_hero_content(None)
        if self._on_selection_changed is not None and emit:
            self._on_selection_changed(None)

    def select_release(self, discogs_release_id: int) -> bool:
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
        button = self._release_id_to_button.get(int(discogs_release_id))
        if button is None:
            return
        button_id = id(button)
        item = self._button_to_item.get(button_id)
        if not isinstance(item, dict):
            return
        normalized_album_id = str(spotify_album_id or "").strip()
        item["spotify_album_id"] = normalized_album_id or None
        self._button_to_item[button_id] = item
        if self._selected_release_id == int(discogs_release_id):
            self._set_hero_links(item)

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

        hero_cover_size = int(min(usable_width * 0.70, usable_height * 0.76))
        hero_cover_size = max(_HERO_MIN_COVER_SIZE, min(_HERO_MAX_COVER_SIZE, hero_cover_size))
        if hero_cover_size != self._hero_cover_size:
            self._hero_cover_size = hero_cover_size
            self._update_hero_content(self._selected_item())

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
