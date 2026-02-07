"""Spin widget placeholder for future animation UI."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


class SpinWheel(Gtk.Box):
    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.set_margin_top(8)
        self.set_margin_bottom(8)
        self.set_margin_start(8)
        self.set_margin_end(8)

        label = Gtk.Label(label="Spin controls will be added in a later phase.")
        label.set_xalign(0.0)
        self.append(label)

