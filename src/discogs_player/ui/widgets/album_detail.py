"""Album detail placeholder widget for future expansion."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


class AlbumDetail(Gtk.Box):
    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_margin_top(8)
        self.set_margin_bottom(8)
        self.set_margin_start(8)
        self.set_margin_end(8)

        title = Gtk.Label(label="Album Detail")
        title.set_xalign(0.0)
        title.add_css_class("title-4")
        self.append(title)

        body = Gtk.Label(
            label="Select a release card to inspect details.\n(Placeholder for MVP GUI scaffold.)"
        )
        body.set_xalign(0.0)
        body.set_wrap(True)
        self.append(body)

