from __future__ import annotations
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk
from collections.abc import Callable
from discogs_player.ui.widgets.spin_wheel import SpinWheel
from discogs_player.ui.widgets.wantlist_detail import WantlistDetail


class WantlistSidebar(Gtk.Box):
    def __init__(
        self,
        *,
        on_spin: Callable[[], None] | None = None,
        on_play_last_spin: Callable[[], None] | None = None,
        on_auto_match: Callable[[], None] | None = None,
        on_override: Callable[[], None] | None = None,
        on_play: Callable[[], None] | None = None,
        on_refresh_tracklist: Callable[[], None] | None = None,
        on_refresh_pricing: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.set_margin_top(8)
        self.set_margin_bottom(8)
        self.set_margin_start(8)
        self.set_margin_end(8)
        self.set_hexpand(True)

        self._spin_wheel = SpinWheel(
            on_spin=on_spin,
            on_play_last_spin=on_play_last_spin,
        )
        self.append(self._spin_wheel)

        # Separator
        self.append(
            Gtk.Separator(
                orientation=Gtk.Orientation.HORIZONTAL, margin_top=10, margin_bottom=10
            )
        )

        self._wantlist_detail = WantlistDetail(
            on_auto_match=on_auto_match,
            on_override=on_override,
            on_play=on_play,
            on_refresh_tracklist=on_refresh_tracklist,
            on_refresh_pricing=on_refresh_pricing,
        )
        self.append(self._wantlist_detail)

    @property
    def spin_wheel(self) -> SpinWheel:
        return self._spin_wheel

    @property
    def wantlist_detail(self) -> WantlistDetail:
        return self._wantlist_detail
