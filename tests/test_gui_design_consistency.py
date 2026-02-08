from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _source_text(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def test_ipod_theme_selectors_exist_in_main_window():
    source = _source_text("src/discogs_player/ui/main_window.py")
    for selector in (
        "window.ipod-shell",
        ".ipod-root",
        ".ipod-panel",
        ".ipod-text-menu",
        ".ipod-carousel",
        ".ipod-cover-strip",
        ".ipod-cover-slot-side",
        ".ipod-cover-slot-center",
        ".ipod-mode-toggle",
        ".ipod-status",
    ):
        assert selector in source


def test_ipod_panel_classes_are_applied_to_major_sections():
    source = _source_text("src/discogs_player/ui/main_window.py")
    for marker in (
        'self._filters.add_css_class("ipod-panel")',
        'self._album_detail.add_css_class("ipod-panel")',
        'self._spin_wheel.add_css_class("ipod-panel")',
        'self._device_picker.add_css_class("ipod-panel")',
        'self._status.add_css_class("ipod-status")',
    ):
        assert marker in source


def test_browse_controls_define_keyboard_and_scroll_navigation():
    source = _source_text("src/discogs_player/ui/main_window.py")
    for marker in (
        "def _handle_key_pressed(",
        "Gdk.KEY_Up",
        "Gdk.KEY_Down",
        "Gdk.KEY_Return",
        "def _handle_browse_scroll(",
        "self._scroll_accum",
    ):
        assert marker in source


def test_filter_sort_options_include_year_and_genre_modes():
    source = _source_text("src/discogs_player/ui/widgets/filters.py")
    for marker in (
        '("year_desc", "Sort: Year (Newest)")',
        '("year_asc", "Sort: Year (Oldest)")',
        '("genre", "Sort: Genre (A-Z)")',
        '("genre_year", "Sort: Genre then Year")',
    ):
        assert marker in source


def test_main_window_resize_fallbacks_are_present():
    source = _source_text("src/discogs_player/ui/main_window.py")
    for marker in (
        "self._filters_scroll = Gtk.ScrolledWindow()",
        "self._filters_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)",
        "content.set_shrink_start_child(True)",
        "content.set_shrink_end_child(True)",
        "self._sidebar_scroll = Gtk.ScrolledWindow()",
        "self._sidebar_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)",
    ):
        assert marker in source


def test_main_window_header_bar_has_window_controls():
    source = _source_text("src/discogs_player/ui/main_window.py")
    for marker in (
        "def _build_window_header_bar() -> Gtk.HeaderBar:",
        "header_bar.set_show_title_buttons(True)",
        'header_bar.set_decoration_layout(":minimize,maximize,close")',
        "self.set_titlebar(_build_window_header_bar())",
    ):
        assert marker in source


def test_smoke_report_includes_runtime_titlebar_presence():
    source = _source_text("src/discogs_player/ui/main_window.py")
    for marker in (
        "titlebar_present = bool(window.get_titlebar() is not None)",
        'report["titlebar_present"] = titlebar_present',
    ):
        assert marker in source


def test_cover_carousel_uses_three_cover_flow_and_prefetches_upcoming_album_art():
    source = _source_text("src/discogs_player/ui/widgets/cover_carousel.py")
    for marker in (
        "_CENTER_SLOT_SIZE =",
        "from discogs_player.services.image_cache import get_or_fetch_cover_path",
        "self._cover_strip = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)",
        "self._left_cover = self._build_cover_slot(",
        "self._center_cover = self._build_cover_slot(",
        "self._right_cover = self._build_cover_slot(",
        "left, center, right = self._slot_indices()",
        "_CAROUSEL_PREFETCH_LOOKAHEAD =",
        "_CAROUSEL_PREFETCH_MAX_WORKERS =",
        "def _prefetch_covers_near_index(self) -> None:",
        "ThreadPoolExecutor(",
        "self._prefetch_executor.submit(",
        "get_or_fetch_cover_path(cover_url)",
        "GLib.idle_add(",
        "self._prefetch_covers_near_index()",
    ):
        assert marker in source


def test_filter_bar_uses_multi_row_layout_for_narrow_widths():
    source = _source_text("src/discogs_player/ui/widgets/filters.py")
    for marker in (
        "super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)",
        "top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)",
        "bottom_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)",
        "self._sort_dropdown.set_hexpand(True)",
    ):
        assert marker in source
