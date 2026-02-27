"""Interactive highest/lowest value lists for Market Dashboard.

Provides clickable album items that navigate back to browse carousel.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Pango

from discogs_player.ui.utils.formatting import format_price


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


class InteractiveValueList(Gtk.Box):
    """
    Interactive list showing highest/lowest value albums with clickable navigation.

    Each album can be clicked to navigate back to the browse carousel.
    """

    def __init__(
        self,
        *,
        title: str,
        items: list[dict[str, Any]],
        on_album_clicked: Callable[[int], None] | None = None,
        on_back_clicked: Callable[[], None] | None = None,
        max_items: int = 10,
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.set_margin_top(12)
        self.set_margin_bottom(12)
        self.set_margin_start(12)
        self.set_margin_end(12)
        self.add_css_class("interactive-value-list")

        self._title = title
        self._on_album_clicked = on_album_clicked
        self._on_back_clicked = on_back_clicked
        self._items = items[:max_items]
        self._max_items = max_items
        self._item_widgets: list[Gtk.Widget] = []

        self._build_header()
        self._build_content()

    def _build_header(self) -> None:
        """Build the list header with title and navigation info."""
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        header_box.set_hexpand(True)

        # Title
        title_label = Gtk.Label(label=self._title)
        title_label.set_xalign(0.0)
        title_label.add_css_class("interactive-list-title")
        title_label.set_hexpand(True)
        header_box.append(title_label)

        # Navigation info
        self._nav_label = Gtk.Label(label=f"Showing {len(self._items)} albums")
        self._nav_label.set_xalign(1.0)
        self._nav_label.add_css_class("interactive-list-nav")
        header_box.append(self._nav_label)

        # Back to carousel button
        if self._on_back_clicked:
            back_button = Gtk.Button(label="← Back to Browse")
            back_button.add_css_class("interactive-back-button")
            back_button.set_tooltip_text("Return to cover carousel")
            back_button.connect("clicked", lambda _: self._on_back_clicked())
            header_box.append(back_button)

        self.append(header_box)

    def _build_content(self) -> None:
        """Build the scrollable content area with album items."""
        # Create scrollable container
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_min_content_height(300)
        scrolled.set_max_content_height(500)

        # Content box for items
        self._content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self._content_box.set_margin_top(8)
        self._content_box.set_margin_bottom(8)
        self._content_box.set_margin_start(8)
        self._content_box.set_margin_end(8)

        scrolled.set_child(self._content_box)
        self.append(scrolled)

        # Build album items
        self._refresh_items()

    def _refresh_items(self) -> None:
        """Clear and rebuild all album items."""
        # Clear existing widgets
        child = self._content_box.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            self._content_box.remove(child)
            child = next_child

        self._item_widgets.clear()

        # Build album items
        if not self._items:
            empty_label = Gtk.Label(label="No albums to display")
            empty_label.add_css_class("interactive-list-empty")
            self._content_box.append(empty_label)
            return

        for item in self._items:
            widget = self._build_album_item(item)
            self._item_widgets.append(widget)
            self._content_box.append(widget)

    def _build_album_item(self, item: dict[str, Any]) -> Gtk.Widget:
        """Build a clickable album item with market value info."""
        # Get album data
        title = item.get("title", "Unknown Title")
        artist = item.get("artist", "Unknown Artist")
        market_value = item.get("market_median") or item.get("market_value", 0.0)
        currency = item.get("market_currency", "")
        year = item.get("year")
        genres = item.get("genres", [])
        discogs_id = item.get("discogs_release_id")

        # Create button for the entire item
        button = Gtk.Button()
        button.add_css_class("interactive-album-button")
        button.set_tooltip_text(f"Click to view: {artist} - {title}")

        # Main container inside button
        item_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        item_box.set_hexpand(True)
        item_box.set_margin_top(8)
        item_box.set_margin_bottom(8)
        item_box.set_margin_start(8)
        item_box.set_margin_end(8)

        # Album cover icon
        cover = Gtk.Image.new_from_icon_name("media-optical-symbolic")
        cover.set_size_request(48, 48)
        cover.add_css_class("interactive-album-cover")
        item_box.append(cover)

        # Album info
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info_box.set_hexpand(True)
        info_box.set_vexpand(True)

        # Title and artist
        title_label = Gtk.Label(label=title)
        title_label.set_xalign(0.0)
        title_label.set_wrap(True)
        title_label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        title_label.add_css_class("interactive-album-title")
        title_label.set_hexpand(True)
        info_box.append(title_label)

        artist_label = Gtk.Label(label=artist)
        artist_label.set_xalign(0.0)
        artist_label.add_css_class("interactive-album-artist")
        artist_label.set_hexpand(True)
        info_box.append(artist_label)

        # Meta row (year, genres)
        meta_parts = []
        if year:
            meta_parts.append(str(year))
        if isinstance(genres, list) and genres:
            genre_text = ", ".join(genres[:2])
            meta_parts.append(genre_text)

        if meta_parts:
            meta_label = Gtk.Label(label=" • ".join(meta_parts))
            meta_label.set_xalign(0.0)
            meta_label.add_css_class("interactive-album-meta")
            meta_label.set_hexpand(True)
            info_box.append(meta_label)

        item_box.append(info_box)

        # Market value
        if market_value:
            price_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            price_box.set_halign(Gtk.Align.END)

            price_label = Gtk.Label(label=format_price(market_value, currency))
            price_label.set_xalign(1.0)
            price_label.add_css_class("interactive-album-price")
            price_box.append(price_label)

            # Discogs ID (small)
            if discogs_id:
                id_label = Gtk.Label(label=f"#{discogs_id}")
                id_label.set_xalign(1.0)
                id_label.add_css_class("interactive-album-id")
                price_box.append(id_label)

            item_box.append(price_box)

        button.set_child(item_box)

        # Connect click handler if we have a release ID
        if isinstance(discogs_id, int) and self._on_album_clicked:
            button.connect(
                "clicked", lambda _, rid=discogs_id: self._handle_album_clicked(rid)
            )

        item_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        item_container.append(button)

        discogs_url = _discogs_release_url(discogs_id)
        marketplace_url = _discogs_marketplace_url(discogs_id)
        if discogs_url or marketplace_url:
            links_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            links_row.set_halign(Gtk.Align.START)
            links_row.set_margin_start(68)
            if discogs_url:
                discogs_link = Gtk.LinkButton.new(discogs_url)
                discogs_link.set_label("Discogs")
                discogs_link.add_css_class("interactive-album-link")
                links_row.append(discogs_link)
            if marketplace_url:
                market_link = Gtk.LinkButton.new(marketplace_url)
                market_link.set_label("Marketplace")
                market_link.add_css_class("interactive-album-link")
                links_row.append(market_link)
            item_container.append(links_row)

        return item_container

    def _handle_album_clicked(self, release_id: int) -> None:
        """Handle album item click - navigate to browse carousel."""
        if self._on_album_clicked:
            self._on_album_clicked(release_id)

    def update_items(self, items: list[dict[str, Any]]) -> None:
        """Update the items in the list."""
        self._items = items[:self._max_items]

        # Update navigation label
        self._nav_label.set_text(f"Showing {len(self._items)} albums")

        # Refresh the display
        self._refresh_items()

    def get_items(self) -> list[dict[str, Any]]:
        """Get the current items."""
        return self._items.copy()
