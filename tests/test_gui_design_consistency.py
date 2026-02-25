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
        ".ipod-gallery",
        ".ipod-gallery-card",
        ".ipod-gallery-hero-frame",
        ".ipod-gallery-back-button",
        ".ipod-cover-strip",
        ".ipod-cover-slot-side",
        ".ipod-cover-slot-center",
        ".ipod-mode-toggle",
        ".ipod-view-row",
        ".ipod-view-switcher",
        ".ipod-value-dashboard",
        ".ipod-value-card",
        ".ipod-value-section",
        ".ipod-value-ops-row",
        ".ipod-value-op-button",
        ".ipod-value-filter-chip",
        ".ipod-value-ops-label",
        ".ipod-value-ops-spin",
        ".ipod-value-ops-status",
        ".ipod-value-detector-group",
        ".ipod-status",
    ):
        assert selector in source


def test_ipod_panel_classes_are_applied_to_major_sections():
    source = _source_text("src/discogs_player/ui/main_window.py")
    for marker in (
        'self._filters.add_css_class("ipod-panel")',
        'self._wantlist_filters.add_css_class("ipod-panel")',
        'self._album_detail.add_css_class("ipod-panel")',
        'self._wantlist_detail.add_css_class("ipod-panel")',
        'self._spin_wheel.add_css_class("ipod-panel")',
        'self._device_picker.add_css_class("ipod-panel")',
        'self._status.add_css_class("ipod-status")',
    ):
        assert marker in source


def test_main_window_exposes_wantlist_tab():
    source = _source_text("src/discogs_player/ui/main_window.py")
    for marker in (
        'self._main_stack.add_titled(wantlist_page, "wantlist", "Wantlist")',
        "from discogs_player.use_cases.browse_wantlist_grid import run_browse_wantlist_grid",
        "from discogs_player.use_cases.sync_wantlist import run_sync_wantlist",
        "from discogs_player.ui.widgets.wantlist_filters import WantlistFilterBar",
        "from discogs_player.ui.widgets.wantlist_detail import WantlistDetail",
    ):
        assert marker in source


def test_main_window_exposes_gallery_mode_for_browse_and_wantlist():
    source = _source_text("src/discogs_player/ui/main_window.py")
    for marker in (
        "from discogs_player.ui.widgets.cover_grid import CoverGrid",
        'self._gallery_mode = Gtk.ToggleButton(label="Gallery")',
        "self._gallery_mode.connect(\"toggled\", self._handle_gallery_mode_toggled)",
        'self._browse_stack.add_named(self._browse_gallery, "gallery")',
        'self._set_browse_mode("gallery")',
        "def _handle_gallery_back_requested(self) -> None:",
        'self._wantlist_gallery_mode = Gtk.ToggleButton(label="Gallery")',
        "self._wantlist_gallery_mode.connect(",
        'self._wantlist_stack.add_named(self._wantlist_gallery, "gallery")',
        'self._set_wantlist_mode("gallery")',
        "def _handle_wantlist_gallery_back_requested(self) -> None:",
    ):
        assert marker in source


def test_browse_controls_define_keyboard_and_scroll_navigation():
    source = _source_text("src/discogs_player/ui/main_window.py")
    for marker in (
        "def _handle_key_pressed(",
        "Gdk.KEY_Up",
        "Gdk.KEY_Down",
        "Gdk.KEY_Return",
        "self._browse_gallery.current_columns()",
        "self._wantlist_gallery.current_columns()",
        "anchor_first_when_unselected=True",
        "def _handle_browse_scroll(",
        "self._scroll_accum",
    ):
        assert marker in source


def test_main_window_uses_id_index_maps_for_gallery_navigation():
    source = _source_text("src/discogs_player/ui/main_window.py")
    for marker in (
        "self._visible_release_id_to_index: dict[int, int] = {}",
        "self._visible_wantlist_id_to_index: dict[int, int] = {}",
        "def _build_id_index_map(ids: list[int]) -> dict[int, int]:",
        "self._visible_release_id_to_index = self._build_id_index_map(",
        "self._visible_wantlist_id_to_index = self._build_id_index_map(",
        "current_index = self._visible_release_id_to_index.get(",
        "current_index = self._visible_wantlist_id_to_index.get(",
    ):
        assert marker in source


def test_mode_toggle_handlers_publish_status_consistently():
    source = _source_text("src/discogs_player/ui/main_window.py")
    for marker in (
        "def _browse_mode_status_text(mode: str) -> str:",
        "def _wantlist_mode_status_text(mode: str) -> str:",
        "def _set_browse_mode_status(self, mode: str) -> None:",
        "def _set_wantlist_mode_status(self, mode: str) -> None:",
        "self._set_browse_mode_status(\"gallery\")",
        "self._set_wantlist_mode_status(\"gallery\")",
        "\"Browse gallery selection cleared.\"",
        "\"Wantlist gallery selection cleared.\"",
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
        "self._sidebar_scroll.set_min_content_width(320)",
        "self._sidebar_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)",
        "content.set_position(850)",
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
        "_CENTER_TO_SIDE_RATIO =",
        "_MIN_CENTER_SLOT_SIZE =",
        "_MIN_SIDE_SLOT_SIZE =",
        "_SIDE_WIDTH_MAX_RATIO_OF_CENTER =",
        "_SIDE_HEIGHT_MAX_RATIO_OF_CENTER =",
        "_RESIZE_DEBOUNCE_MS =",
        "from discogs_player.services.image_cache import get_or_fetch_cover_path",
        "self._cover_strip = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)",
        "self._cover_strip.set_halign(Gtk.Align.CENTER)",
        "self._left_cover = self._build_cover_slot(",
        "self._center_cover = self._build_cover_slot(",
        "self._right_cover = self._build_cover_slot(",
        "self._cover_strip.append(self._left_cover)",
        "self._cover_strip.append(self._center_cover)",
        "self._cover_strip.append(self._right_cover)",
        "left = (center - 1) % count",
        "right = (center + 1) % count",
        "left, center, right = self._slot_indices()",
        "_CAROUSEL_PREFETCH_LOOKAHEAD =",
        "_CAROUSEL_PREFETCH_MAX_WORKERS =",
        "def _prefetch_covers_near_index(self) -> None:",
        "ThreadPoolExecutor(",
        "self._prefetch_executor.submit(",
        "get_or_fetch_cover_path(cover_url)",
        "GLib.idle_add(",
        "self._prefetch_covers_near_index()",
        "def _compute_responsive_slot_sizes(",
        "self._SIDE_WIDTH_MAX_RATIO_OF_CENTER",
        "self._SIDE_HEIGHT_MAX_RATIO_OF_CENTER",
        "def _apply_responsive_slot_sizes(",
        "def _coerce_layout_hint_dimensions(",
        "self._last_stable_hint_width",
        "self._last_stable_hint_height",
        "def _schedule_responsive_slot_update(",
        "def _flush_pending_responsive_slot_update(",
        "def _on_size_change(",
        "_CENTER_SPIN_INTERVAL_MS =",
        "_CENTER_SPIN_MIN_TICKS =",
        "def start_center_spin_animation(self",
        "def stop_center_spin_animation(self",
        "self._center_spin_source_id: int | None = None",
        "self._center_spin_target_release_id: int | None = None",
        "def set_spin_target_release(self, discogs_release_id: int | None) -> None:",
        "def _spin_stride_for_remaining(remaining: int) -> int:",
        "self._index = next_index",
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


def test_cover_grid_widget_supports_gallery_selection_overlay_and_back_action():
    source = _source_text("src/discogs_player/ui/widgets/cover_grid.py")
    for marker in (
        "class CoverGrid(Gtk.Box):",
        "self._hero_revealer = Gtk.Revealer()",
        'self._back_button = Gtk.Button(label="Back to Gallery")',
        'self._back_button.add_css_class("interactive-back-button")',
        "def clear_selection(self, *, emit: bool = True) -> None:",
        "def has_active_selection(self) -> bool:",
        "def apply_layout_hint(",
    ):
        assert marker in source


def test_cover_grid_uses_incremental_selection_and_layout_updates():
    source = _source_text("src/discogs_player/ui/widgets/cover_grid.py")
    for marker in (
        "self._buttons_by_id: dict[int, Gtk.Button] = {}",
        "self._selected_button_id: int | None = None",
        "_RESIZE_DEBOUNCE_MS =",
        "self._pending_layout_source_id: int | None = None",
        "self.connect(\"destroy\", self._handle_destroy)",
        "def _schedule_responsive_layout(self) -> None:",
        "def _flush_pending_responsive_layout(self) -> bool:",
        "def _cancel_pending_responsive_layout(self) -> None:",
        "GLib.timeout_add(",
        "def _hero_key_for_item(self, item: dict[str, object]) -> tuple[int | None, str, int]:",
        "if self._selected_button_id == next_button_id:",
        "layout_changed = (",
        "if layout_changed:",
    ):
        assert marker in source


def test_main_window_tracklist_detail_cache_paths_exist():
    source = _source_text("src/discogs_player/ui/main_window.py")
    for marker in (
        "from collections import OrderedDict",
        "_TRACKLIST_DETAIL_CACHE_LIMIT =",
        "self._release_tracklist_cache: OrderedDict[int, dict[str, object]] = (",
        "self._wantlist_tracklist_cache: OrderedDict[int, dict[str, object]] = (",
        "def _tracklist_cache_get(",
        "def _tracklist_cache_put(",
        "def _tracklist_cache_invalidate(",
        "self._tracklist_cache_put(",
        "self._tracklist_cache_invalidate(",
    ):
        assert marker in source


def test_main_window_exposes_market_value_dashboard_tab_and_data_refresh_hooks():
    source = _source_text("src/discogs_player/ui/main_window.py")
    for marker in (
        "from discogs_player.core.settings import get_int_setting, set_setting",
        "from discogs_player.use_cases.value_dashboard import run_market_value_dashboard",
        "from discogs_player.use_cases.value_missing import run_market_value_missing",
        "from discogs_player.use_cases.value_refresh import run_refresh_market_values",
        "from discogs_player.use_cases.value_snapshot import run_market_value_snapshot",
        '_SETTING_VALUE_OPS_STALE_DAYS = "gui_value_ops_stale_days"',
        '_SETTING_VALUE_OPS_REFRESH_LIMIT = "gui_value_ops_refresh_limit"',
        "_VALUE_DASHBOARD_TOP_LIMIT = 25",
        "_VALUE_DASHBOARD_BOTTOM_LIMIT = 25",
        "_VALUE_DASHBOARD_TREND_LIMIT = 12",
        "from discogs_player.ui.widgets.value_dashboard import ValueDashboard",
        "self._value_ops_executor = ThreadPoolExecutor(",
        "self._main_stack = Gtk.Stack()",
        "self._main_stack_switcher = Gtk.StackSwitcher()",
        'self._main_stack.add_titled(browse_page, "browse", "Browse")',
        'self._browse_stack.set_visible_child_name("carousel")',
        "self._carousel_mode.set_active(True)",
        'self._set_browse_mode("carousel")',
        "self._value_dashboard = ValueDashboard(",
        "on_ops_controls_changed=self._handle_value_ops_controls_changed",
        "self._value_dashboard.set_ops_controls(",
        "def _load_value_ops_controls_from_settings(self) -> tuple[int, int]:",
        "get_int_setting(",
        "def _persist_value_ops_controls_to_settings(self) -> None:",
        "set_setting(_SETTING_VALUE_OPS_STALE_DAYS, str(stale_days))",
        "set_setting(_SETTING_VALUE_OPS_REFRESH_LIMIT, str(refresh_limit))",
        'self._main_stack.add_titled(\n            self._value_dashboard_scroll, "value", "Market Value"\n        )',
        "def _refresh_value_dashboard(",
        "top_limit=_VALUE_DASHBOARD_TOP_LIMIT",
        "bottom_limit=_VALUE_DASHBOARD_BOTTOM_LIMIT",
        "trend_limit=_VALUE_DASHBOARD_TREND_LIMIT",
        "def _start_value_operation(",
        "def _handle_value_refresh_missing_clicked(self) -> None:",
        "def _handle_value_refresh_stale_clicked(self) -> None:",
        "def _handle_value_snapshot_clicked(self) -> None:",
        "refresh_limit = self._value_dashboard.refresh_limit()",
        "stale_days = self._value_dashboard.stale_days()",
        "self._spin_wheel.set_context_release(item)",
        "self._spin_wheel.set_context_release(None)",
        "def _normalize_refresh_limit(value: int) -> int:",
        "def _normalize_stale_days(value: int) -> int:",
        'return str(visible or "carousel")',
        "limit=effective_limit,",
        "stale_days=effective_stale_days,",
        "GLib.idle_add(",
        "def _handle_value_dashboard_release_selected(self, discogs_release_id: int) -> None:",
    ):
        assert marker in source


def test_album_detail_and_spin_widgets_include_market_pricing_context():
    album_source = _source_text("src/discogs_player/ui/widgets/album_detail.py")
    for marker in (
        'self._market_value_label = Gtk.Label(label="Market: n/a")',
        'self._market_metrics_label = Gtk.Label(label="Metrics: n/a")',
        "self._discogs_grid = Gtk.Grid()",
        'self._discogs_genres_value = self._add_discogs_row(0, "Genres")',
        'self._discogs_synced_value = self._add_discogs_row(3, "Last Sync")',
        'self._tracklist_heading = Gtk.Label(label="Tracklist")',
        'self._tracklist_meta = Gtk.Label(label="Tracklist cache: n/a")',
        'self._tracklist_body = Gtk.Label(label="No release selected.")',
        'self._refresh_tracklist_button = Gtk.Button(label="Refresh Tracklist")',
        "on_refresh_tracklist: Callable[[], None] | None = None",
        "self._refresh_tracklist_button.set_sensitive(enabled)",
        "def _add_discogs_row(self, row: int, key_text: str) -> Gtk.Label:",
        "def _set_discogs_extract_defaults(self) -> None:",
        "def _set_discogs_extract_values(self, item: dict[str, object]) -> None:",
        "def _set_tracklist_defaults(self) -> None:",
        "def _set_tracklist_values(self, item: dict[str, object]) -> None:",
        'key_label = Gtk.Label(label=f"{key_text}:")',
        'value_label = Gtk.Label(label="n/a")',
        "self._market_value_label.set_text(format_market_summary(item))",
        "self._market_metrics_label.set_text(format_market_metrics(item))",
        "self._set_discogs_extract_defaults()",
        "self._set_discogs_extract_values(item)",
        "self._set_tracklist_defaults()",
        "self._set_tracklist_values(item)",
    ):
        assert marker in album_source

    spin_source = _source_text("src/discogs_player/ui/widgets/spin_wheel.py")
    for marker in (
        'self._selected_market_label = Gtk.Label(label="Selected Market: n/a")',
        "def set_context_release(self, item: dict[str, object] | None) -> None:",
        'self._selected_market_label.set_text("Selected Market: loading...")',
        "self._selected_market_label.set_text(format_market_summary(release))",
    ):
        assert marker in spin_source


def test_main_window_wires_tracklist_refresh_action():
    source = _source_text("src/discogs_player/ui/main_window.py")
    for marker in (
        "from discogs_player.use_cases.tracklist_show import run_release_tracklist_show",
        "on_refresh_tracklist=self._handle_tracklist_refresh_clicked",
        "def _handle_tracklist_refresh_clicked(self) -> None:",
        "runner=lambda rid=release_id: run_release_tracklist_show(rid, refresh=True)",
        "def _apply_tracklist_refresh_result(self, payload: dict[str, object]) -> None:",
        "detail_item = self._release_with_cached_tracklist(selected)",
        'f"Tracklist refreshed for release {release_id_text} ({audio_count}/{track_count} audio tracks)."',
    ):
        assert marker in source


def test_main_window_uses_async_action_runner_for_interactive_operations():
    source = _source_text("src/discogs_player/ui/main_window.py")
    for marker in (
        "self._actions_executor = ThreadPoolExecutor(",
        'thread_name_prefix="ui-actions"',
        "self._inflight_actions: set[str] = set()",
        "def _start_async_action(",
        "def _complete_async_action(",
        'action_key="browse-load"',
        'action_key="album-action"',
        'action_key="device-action"',
        'action_key="browse-spin-action"',
        'action_key="spin-play-last"',
        "self._carousel.start_center_spin_animation(",
        "self._carousel.set_spin_target_release(release_id)",
        "self._carousel.stop_center_spin_animation()",
    ):
        assert marker in source


def test_main_window_preserves_previous_selection_across_refreshes():
    source = _source_text("src/discogs_player/ui/main_window.py")
    for marker in (
        "preferred_release_id = self._selected_release_id",
        "def _apply_release_load_result(",
        "preferred_release_id: int | None,",
        "restored_selection = False",
        "if isinstance(preferred_release_id, int):",
        "restored_selection = self._focus_release_id(",
        "if not restored_selection and items:",
        'first_release_id = items[0].get("discogs_release_id")',
    ):
        assert marker in source


def test_spin_wheel_supports_start_then_complete_animation_flow():
    source = _source_text("src/discogs_player/ui/widgets/spin_wheel.py")
    for marker in (
        "def start_spin_animation(",
        "def complete_spin_animation(self, payload: dict[str, object]) -> None:",
        "self.start_spin_animation(on_complete=on_complete)",
        "self.complete_spin_animation(payload)",
        "if payload is None:",
        "return True",
    ):
        assert marker in source


def test_device_picker_exposes_action_busy_state_controls():
    source = _source_text("src/discogs_player/ui/widgets/device_picker.py")
    for marker in (
        "self._actions_enabled = True",
        "def _apply_control_sensitivity(self) -> None:",
        "def set_actions_enabled(self, enabled: bool) -> None:",
        "self._refresh_button.set_sensitive(controls_enabled)",
        "self._set_default_button.set_sensitive(controls_enabled and has_devices)",
    ):
        assert marker in source


def test_wantlist_detail_uses_public_actions_toggle_method():
    source = _source_text("src/discogs_player/ui/widgets/wantlist_detail.py")
    assert "def set_actions_enabled(self, enabled: bool) -> None:" in source
    assert "self.set_actions_enabled(True)" in source
    assert "self._set_actions_enabled(" not in source


def test_wantlist_detail_includes_spotify_controls_and_capability_states():
    source = _source_text("src/discogs_player/ui/widgets/wantlist_detail.py")
    for marker in (
        "on_auto_match: Callable[[], None] | None = None",
        "on_override: Callable[[], None] | None = None",
        "on_play: Callable[[], None] | None = None",
        'self._mapping_label = Gtk.Label(label="Mapping: none")',
        'self._candidate_label = Gtk.Label(label="Candidate: none")',
        "self._spotify_hint_label = Gtk.Label(label=\"\")",
        'self._match_button = Gtk.Button(label="Auto Match")',
        'self._play_button = Gtk.Button(label="Play")',
        "def set_spotify_capability(",
        'hint = action_label or "Enable Spotify (optional)"',
        'hint = action_label or "Connect Spotify"',
        'self._play_button.set_label("Open in Spotify")',
        "def set_match_result(self, payload: dict[str, object]) -> None:",
        "def set_override_result(self, payload: dict[str, object]) -> None:",
        "def set_play_result(self, payload: dict[str, object]) -> None:",
    ):
        assert marker in source


def test_main_window_wires_wantlist_spotify_actions_like_browse():
    source = _source_text("src/discogs_player/ui/main_window.py")
    for marker in (
        "on_auto_match=self._handle_wantlist_auto_match_clicked",
        "on_override=self._handle_wantlist_override_clicked",
        "on_play=self._handle_wantlist_play_clicked",
        "self._wantlist_detail.set_spotify_capability(",
        "def _handle_wantlist_auto_match_clicked(self) -> None:",
        "def _handle_wantlist_override_clicked(self) -> None:",
        "def _handle_wantlist_play_clicked(self) -> None:",
        "self._wantlist_detail.set_match_result(payload)",
        "self._wantlist_detail.set_override_result(payload)",
        "self._wantlist_detail.set_play_result(payload)",
        "self._wantlist_spin_wheel.set_context_release(detail_item)",
    ):
        assert marker in source


def test_value_dashboard_widget_renders_summary_lists_and_charts():
    source = _source_text("src/discogs_player/ui/widgets/value_dashboard.py")
    for marker in (
        "class ValueDashboard(Gtk.Box):",
        'title = Gtk.Label(label="Collection Value Dashboard")',
        'self._build_summary_card("Total Low")',
        'self._build_summary_card("Total Median")',
        'self._build_summary_card("Total High")',
        'self._build_section("Top 25 Priced")',
        'self._build_section("Bottom 25 Priced")',
        'self._build_section(\n            "Median Trend (Snapshots)"\n        )',
        'self._build_section("Likely Duplicates")',
        'self._build_section("Variant Families")',
        'self._detector_confidence_chip = Gtk.Label(label="Detector confidence n/a")',
        'self._duplicate_only_chip = Gtk.ToggleButton(label="Duplicates only")',
        'self._variant_only_chip = Gtk.ToggleButton(label="Variants only")',
        "self._detector_revealer = self._build_revealer()",
        "def _set_detector_confidence_chip(self, score: object) -> None:",
        "def _handle_detector_chip_toggled(",
        "def _set_detector_filter_mode(self, mode: str, *, sync_buttons: bool) -> None:",
        "def _apply_detector_filter(self) -> None:",
        "def _build_bar_row(",
        "def _append_detector_groups(",
        "def _build_detector_item_label(",
        "def _append_release_rows(",
        "def set_dashboard(self, report: dict[str, object]) -> None:",
    ):
        assert marker in source


def test_value_dashboard_widget_exposes_market_ops_controls_and_status():
    source = _source_text("src/discogs_player/ui/widgets/value_dashboard.py")
    for marker in (
        "on_ops_controls_changed: Callable[[], None] | None = None",
        "self._on_ops_controls_changed = on_ops_controls_changed",
        'stale_days_label = Gtk.Label(label="Stale Days")',
        "self._stale_days_spin = Gtk.SpinButton()",
        'refresh_limit_label = Gtk.Label(label="Refresh Limit")',
        "self._refresh_limit_spin = Gtk.SpinButton()",
        'self._refresh_missing_button = Gtk.Button(label="Refresh Missing")',
        'self._refresh_stale_button = Gtk.Button(label="Refresh Stale")',
        'self._snapshot_now_button = Gtk.Button(label="Snapshot Now")',
        "self._ops_spinner = Gtk.Spinner()",
        'self._ops_status = Gtk.Label(label="Market ops idle.")',
        "def stale_days(self) -> int:",
        "def refresh_limit(self) -> int:",
        "def set_ops_controls(self, *, stale_days: int, refresh_limit: int) -> None:",
        "def _handle_ops_controls_changed(self, _spin: Gtk.SpinButton) -> None:",
        "def set_ops_busy(self, message: str) -> None:",
        "def set_ops_result(self, message: str) -> None:",
    ):
        assert marker in source


def test_detail_widgets_expose_spotify_links_help_links_and_value_jump_actions():
    album_source = _source_text("src/discogs_player/ui/widgets/album_detail.py")
    wantlist_source = _source_text("src/discogs_player/ui/widgets/wantlist_detail.py")
    for marker in (
        'self._spotify_mapping_link_button = Gtk.LinkButton.new(',
        'self._spotify_mapping_link_button.set_label("Spotify album link unavailable")',
        "self._spotify_help_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)",
        "self._spotify_dashboard_link = Gtk.LinkButton.new(_SPOTIFY_DASHBOARD_URL)",
        "self._spotify_oauth_guide_link = Gtk.LinkButton.new(_SPOTIFY_OAUTH_GUIDE_URL)",
        'self._view_market_value_button = Gtk.Button(',
        "def _set_spotify_mapping_link(self, album_id_value: object | None) -> None:",
        "self._spotify_help_row.set_visible(bool(self._spotify_hint_label.get_text()))",
    ):
        assert marker in album_source
        assert marker in wantlist_source


def test_cover_grid_hero_overlay_includes_external_action_links():
    source = _source_text("src/discogs_player/ui/widgets/cover_grid.py")
    for marker in (
        "self._hero_actions_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)",
        'self._hero_discogs_link = Gtk.LinkButton.new("https://www.discogs.com")',
        'self._hero_marketplace_link = Gtk.LinkButton.new("https://www.discogs.com")',
        "self._hero_spotify_link = Gtk.LinkButton.new(_SPOTIFY_HOME_URL)",
        "def _set_hero_links(self, item: dict[str, object] | None) -> None:",
        "def set_release_spotify_album_id(",
    ):
        assert marker in source


def test_main_window_exposes_help_menu_and_detail_to_value_navigation_hooks():
    source = _source_text("src/discogs_player/ui/main_window.py")
    for marker in (
        "self._install_header_help_menu(titlebar)",
        "def _install_header_help_menu(self, header_bar: Gtk.HeaderBar) -> None:",
        "Open README",
        "Open Product State",
        "Open Spotify Walkthrough",
        "Setup Commands",
        "on_view_market_value=self._handle_view_market_value_clicked",
        "on_view_market_value=self._handle_wantlist_view_market_value_clicked",
        "def _focus_value_dashboard_release(self, discogs_release_id: int, *, source: str) -> None:",
        "def _handle_view_market_value_clicked(self) -> None:",
        "def _handle_wantlist_view_market_value_clicked(self) -> None:",
    ):
        assert marker in source


def test_value_dashboard_supports_empty_state_actions_and_row_highlighting():
    source = _source_text("src/discogs_player/ui/widgets/value_dashboard.py")
    for marker in (
        "on_open_docs: Callable[[], None] | None = None",
        "self._on_refresh_missing_action = on_refresh_missing",
        "self._on_open_docs = on_open_docs",
        'refresh_button = Gtk.Button(label="Refresh Market Values")',
        'docs_button = Gtk.Button(label="Open Docs")',
        "def _clear_release_row_registry(self) -> None:",
        "def _register_release_row_button(",
        "def highlight_release(self, discogs_release_id: int) -> bool:",
        'button.add_css_class("is-highlighted")',
    ):
        assert marker in source
