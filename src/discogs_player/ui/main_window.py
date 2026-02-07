"""Main GTK window for Discogs Player."""

from __future__ import annotations

import json
import traceback

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from discogs_player.use_cases.browse_release_grid import run_browse_release_grid
from discogs_player.ui.widgets.album_detail import AlbumDetail
from discogs_player.ui.widgets.cover_grid import CoverGrid
from discogs_player.ui.widgets.device_picker import DevicePicker
from discogs_player.ui.widgets.filters import FilterBar
from discogs_player.ui.widgets.spin_wheel import SpinWheel


class MainWindow(Adw.ApplicationWindow):
    def __init__(
        self,
        app: Adw.Application,
        *,
        limit: int = 50,
        preload_covers: bool = True,
    ) -> None:
        super().__init__(application=app, title="Discogs Player")
        self.set_default_size(1200, 820)

        self._limit = max(1, int(limit))
        self._preload_covers = bool(preload_covers)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_content(root)

        self._filters = FilterBar(on_refresh=self.refresh)
        root.append(self._filters)

        content = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)
        content.set_resize_start_child(True)
        content.set_shrink_start_child(False)
        content.set_resize_end_child(True)
        root.append(content)

        self._cover_grid = CoverGrid()
        content.set_start_child(self._cover_grid)

        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        sidebar.set_margin_top(8)
        sidebar.set_margin_bottom(8)
        sidebar.set_margin_start(8)
        sidebar.set_margin_end(8)
        content.set_end_child(sidebar)

        sidebar.append(AlbumDetail())
        sidebar.append(SpinWheel())
        sidebar.append(DevicePicker())

        self._status = Gtk.Label(label="Ready")
        self._status.set_xalign(0.0)
        self._status.set_margin_top(6)
        self._status.set_margin_bottom(8)
        self._status.set_margin_start(12)
        self._status.set_margin_end(12)
        root.append(self._status)

    def refresh(self) -> dict[str, object]:
        query = self._filters.search_text()
        return self.load_releases(q=query)

    def load_releases(self, *, q: str | None = None) -> dict[str, object]:
        self._status.set_text("Loading releases...")
        items = run_browse_release_grid(
            limit=self._limit,
            q=q,
            preload_covers=self._preload_covers,
        )

        self._cover_grid.set_items(items)
        cover_count = sum(1 for item in items if item.get("cover_path"))
        self._status.set_text(f"Loaded {len(items)} releases ({cover_count} covers cached)")
        return {
            "ok": True,
            "item_count": len(items),
            "cover_cached_count": cover_count,
            "query": q,
        }


class DiscogsPlayerApp(Adw.Application):
    def __init__(self, *, limit: int = 50, preload_covers: bool = True, smoke_test: bool = False):
        super().__init__(application_id="com.discogs_player.app")
        self._limit = max(1, int(limit))
        self._preload_covers = bool(preload_covers)
        self._smoke_test = bool(smoke_test)
        self.exit_code = 0
        self._did_activate = False

    def do_activate(self) -> None:  # pragma: no cover - driven by integration runtime
        if self._did_activate:
            return
        self._did_activate = True

        window = MainWindow(self, limit=self._limit, preload_covers=self._preload_covers)
        window.present()

        try:
            report = window.load_releases()
        except Exception as exc:
            self.exit_code = 1
            report = {
                "ok": False,
                "error": str(exc),
                "traceback": traceback.format_exc(limit=4),
            }

        if self._smoke_test:
            print(json.dumps(report, sort_keys=True))
            self.quit()

