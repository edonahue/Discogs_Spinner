"""Main GTK window for Discogs Player."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime
import json
from pathlib import Path
import sys
import time
import traceback

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, GLib, Gtk

from discogs_player.capabilities import get_capabilities
from discogs_player.core.settings import (
    get_discogs_token,
    get_int_setting,
    get_setting,
    set_setting,
)
from discogs_player.use_cases.sync_collection import run_sync_collection
from discogs_player.integrations.player_backend import (
    PlayerApiError,
    PlayerAuthError,
    PlayerDependencyError,
    PlayerPlaybackError,
)
from discogs_player.services.matching import MatchingDependencyError
from discogs_player.services.discogs_client import (
    DiscogsApiError,
    DiscogsAuthError,
    DiscogsDependencyError,
)
from discogs_player.services.sync_manager import MissingDiscogsTokenError
from discogs_player.use_cases.browse_release_grid import run_browse_release_grid
from discogs_player.use_cases.browse_wantlist_grid import run_browse_wantlist_grid
from discogs_player.use_cases.device_management import NoSpotifyDevicesError
from discogs_player.use_cases.device_picker_flow import (
    run_auto_set_default_device_action,
    run_refresh_devices_action,
    run_set_default_device_action,
)
from discogs_player.use_cases.match_play_flow import (
    run_match_audit_action,
    run_match_action,
    run_match_review_apply_action,
    run_match_review_reject_action,
    run_match_retry_errors_action,
    run_override_action,
    run_play_action,
)
from discogs_player.use_cases.play_release import MissingLastSpinError
from discogs_player.use_cases.spin_flow import (
    run_play_last_spin_action,
    run_spin_action,
)
from discogs_player.use_cases.spin_wantlist import run_spin_wantlist
from discogs_player.use_cases.tracklist_cached import run_release_tracklist_cached
from discogs_player.use_cases.tracklist_show import run_release_tracklist_show
from discogs_player.use_cases.sync_wantlist import run_sync_wantlist
from discogs_player.use_cases.wantlist_tracklist_cached import (
    run_wantlist_tracklist_cached,
)
from discogs_player.use_cases.wantlist_tracklist_show import run_wantlist_tracklist_show
from discogs_player.use_cases.wantlist_value_refresh import (
    run_refresh_wantlist_market_value,
)
from discogs_player.use_cases.collection_health import run_collection_health
from discogs_player.use_cases.value_dashboard import run_market_value_dashboard
from discogs_player.use_cases.value_refresh_queue import run_value_refresh_queue
from discogs_player.use_cases.value_missing import run_market_value_missing
from discogs_player.use_cases.value_refresh import run_refresh_market_values
from discogs_player.use_cases.value_snapshot import run_market_value_snapshot
from discogs_player.ui.sorting import sort_release_items
from discogs_player.ui.widgets.album_detail import AlbumDetail

def _format_sync_date(iso_str: str | None) -> str:
    """Return a short human-readable sync date from an ISO-8601 timestamp.

    Returns "never" for None/empty, or "YYYY-MM-DD" on parse failure.
    """
    if not iso_str:
        return "never"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        local = dt.astimezone()
        return f"{local.year}-{local.month:02d}-{local.day:02d}"
    except (ValueError, AttributeError):
        return iso_str[:10] if iso_str else "never"


# Set to True via set_timing_enabled() (or --timing CLI flag) to print
# per-operation latency samples to stderr during a session.
_TIMING_ENABLED: bool = False


def set_timing_enabled(enabled: bool) -> None:
    """Enable or disable per-operation latency logging to stderr."""
    global _TIMING_ENABLED
    _TIMING_ENABLED = bool(enabled)


from discogs_player.ui.dialogs.preferences_window import PreferencesWindow
from discogs_player.ui.dialogs.setup_wizard import SetupWizard
from discogs_player.ui.widgets.cover_carousel import CoverCarousel
from discogs_player.ui.widgets.cover_grid import CoverGrid
from discogs_player.ui.widgets.device_picker import DevicePicker
from discogs_player.ui.widgets.filters import FilterBar
from discogs_player.ui.widgets.spin_wheel import SpinWheel
from discogs_player.ui.widgets.text_menu import ReleaseTextMenu
from discogs_player.ui.widgets.health_score import HealthScoreWidget
from discogs_player.ui.widgets.value_dashboard import ValueDashboard
from discogs_player.ui.widgets.value_queue import ValueQueueWidget
from discogs_player.ui.widgets.wantlist_detail import WantlistDetail
from discogs_player.ui.widgets.wantlist_filters import WantlistFilterBar

_IPOD_NANO_CSS = """
window.ipod-shell {
  background-image: linear-gradient(180deg, #0f1115 0%, #07080a 45%, #030405 100%);
}

.ipod-root {
  background-image: radial-gradient(circle at top, #171b22 0%, #0a0d12 50%, #050607 100%);
}

.ipod-mode-row {
  padding: 6px 8px;
}

.ipod-mode-spin.ipod-panel {
  border: none;
  background-color: transparent;
  padding: 0;
}

.ipod-mode-title {
  color: #d3d7df;
  font-weight: 700;
}

.ipod-mode-toggle {
  border-radius: 18px;
  padding: 5px 12px;
}

.ipod-panel {
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background-color: rgba(8, 11, 16, 0.84);
  padding: 8px;
}

.ipod-panel label {
  color: #d8dee9;
}

.ipod-panel .title-4 {
  color: #eef2f8;
}

.ipod-filter-bar {
  border-radius: 12px;
}

.ipod-empty-state {
  padding: 32px;
}

.ipod-empty-state-label {
  color: #8a9ab0;
  font-size: 1.05em;
  margin-bottom: 4px;
}

.ipod-empty-state-button {
  margin-top: 8px;
  min-width: 160px;
}

.ipod-ftux-card {
  background: radial-gradient(ellipse at top, rgba(22, 40, 68, 0.92), rgba(6, 10, 18, 0.97));
  border: 1px solid rgba(96, 150, 196, 0.38);
  border-radius: 18px;
  padding: 36px 40px;
}

.ipod-ftux-icon {
  color: #5b8dbf;
}

.ipod-ftux-heading {
  font-size: 1.2em;
  font-weight: 700;
  color: #d8eaf8;
}

button.ipod-ftux-cta {
  margin-top: 8px;
  min-width: 176px;
}

.ipod-status {
  color: #b9c4d6;
}

.ipod-text-menu,
.ipod-carousel {
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background-color: rgba(8, 11, 16, 0.92);
}

.ipod-gallery {
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background-color: rgba(8, 11, 16, 0.92);
}

.ipod-gallery-grid {
  padding: 2px;
}

button.ipod-gallery-card {
  border-radius: 12px;
  border: 1px solid rgba(145, 164, 194, 0.22);
  background-image: linear-gradient(
    160deg,
    rgba(25, 34, 49, 0.82),
    rgba(10, 14, 22, 0.94)
  );
  padding: 0;
}

button.ipod-gallery-card:hover {
  border-color: rgba(150, 197, 255, 0.55);
  background-image: linear-gradient(
    160deg,
    rgba(33, 45, 65, 0.92),
    rgba(14, 20, 31, 0.98)
  );
}

button.ipod-gallery-card.is-selected {
  border-color: rgba(133, 188, 255, 0.88);
  box-shadow: 0 14px 36px rgba(0, 0, 0, 0.42);
}

.ipod-gallery-cover-frame {
  border-radius: 10px;
  border: 1px solid rgba(148, 170, 205, 0.32);
  background-color: rgba(4, 7, 12, 0.94);
}

.ipod-gallery-card-title {
  color: #eff5ff;
  font-weight: 700;
  font-size: 13px;
}

.ipod-gallery-card-subtitle {
  color: #9fb2cc;
  font-size: 11px;
  font-weight: 600;
}

.ipod-gallery-hero-scrim {
  background-color: rgba(3, 6, 12, 0.74);
}

.ipod-gallery-hero-shell {
  padding: 14px 16px;
}

.ipod-gallery-hero-frame {
  border-radius: 14px;
  border: 1px solid rgba(148, 192, 255, 0.56);
  background-color: rgba(5, 9, 14, 0.97);
  box-shadow: 0 18px 52px rgba(0, 0, 0, 0.5);
}

.ipod-gallery-hero-title {
  color: #eff5ff;
  font-size: 20px;
  font-weight: 800;
}

.ipod-gallery-hero-subtitle {
  color: #adc0dc;
  font-size: 13px;
  font-weight: 600;
}

.ipod-gallery-back-button {
  min-height: 42px;
  min-width: 192px;
  font-size: 14px;
  font-weight: 700;
}

.ipod-gallery-hero-actions {
  margin-top: 2px;
}

.ipod-gallery-hero-action {
  border-radius: 999px;
  border: 1px solid rgba(158, 197, 250, 0.45);
  background-color: rgba(18, 26, 40, 0.9);
  color: #dceaff;
  font-size: 11px;
  font-weight: 700;
  padding: 5px 10px;
}

.ipod-gallery-placeholder {
  color: #7f8ba0;
}

.ipod-gallery-placeholder-caption {
  color: #8191a8;
  font-size: 11px;
}

.ipod-menu-row {
  border-radius: 10px;
}

.ipod-menu-primary {
  color: #f2f4f8;
  font-weight: 600;
}

.ipod-menu-secondary,
.ipod-menu-chevron,
.ipod-carousel-meta {
  color: #93a1b8;
}

.ipod-carousel-title {
  color: #e9edf5;
  font-weight: 700;
  font-size: 18px;
  margin-bottom: 4px;
}

.ipod-artist-album-title {
  color: #eef2f8;
  font-weight: 700;
  font-size: 18px;
  line-height: 1.35;
  margin-bottom: 16px;
  padding: 14px;
  background-color: rgba(255, 255, 255, 0.09);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.18);
}

/* Responsive design for better window resizing */
.ipod-root {
  min-width: 800px;
  min-height: 600px;
}

/* Adjust for smaller windows */
.ipod-root.ipod-width-compact .ipod-artist-album-title {
  font-size: 18px;
  padding: 6px;
}

.ipod-root.ipod-width-ultra-compact .ipod-artist-album-title {
  font-size: 16px;
  padding: 4px;
}

.ipod-root.ipod-width-ultra-compact .ipod-panel {
  padding: 4px;
}

.ipod-carousel-meta {
  color: #8e9eab;
  font-size: 12px;
  margin-bottom: 8px;
}

.ipod-cover-strip {
  padding: 2px;
}

.ipod-cover-frame {
  margin: 4px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background-color: rgba(4, 6, 9, 0.95);
}

.ipod-cover-slot {
  margin: 1px;
}

.ipod-cover-slot-side {
  opacity: 0.64;
}

.ipod-cover-slot-center {
  border: 1px solid rgba(174, 200, 255, 0.45);
  box-shadow: 0 10px 24px rgba(0, 0, 0, 0.38);
}

.ipod-cover-placeholder {
  color: #7f8ba0;
  font-size: 22px;
}

.ipod-view-row {
  padding: 8px 10px 6px 10px;
}

.ipod-view-title {
  color: #d3d7df;
  font-weight: 700;
}

.ipod-view-switcher {
  border-radius: 12px;
}

.ipod-help-menu-button {
  border-radius: 999px;
}

.ipod-value-dashboard {
  padding: 6px;
  font-family: "SF Pro Display", "SF Pro Text", "Helvetica Neue", "Cantarell", sans-serif;
}

.ipod-value-kicker {
  color: #9eb2cf;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1.05px;
}

.ipod-value-dashboard-title {
  color: #f1f6ff;
  font-size: 30px;
  font-weight: 800;
  letter-spacing: -0.35px;
}

.ipod-value-chip {
  border-radius: 999px;
  border: 1px solid rgba(186, 204, 232, 0.35);
  background-color: rgba(22, 30, 45, 0.88);
  color: #dbe7ff;
  font-size: 12px;
  font-weight: 700;
  padding: 5px 12px;
}

.ipod-value-chip.is-positive {
  border-color: rgba(86, 215, 144, 0.55);
  color: #8be7b2;
}

.ipod-value-chip.is-negative {
  border-color: rgba(244, 113, 113, 0.55);
  color: #f5a3a3;
}

.ipod-value-subtitle {
  color: #b8c6dd;
  font-size: 13px;
  font-weight: 500;
  letter-spacing: 0.08px;
  margin-bottom: 4px;
}

.ipod-value-ops-row {
  margin-bottom: 2px;
}

.ipod-value-op-button {
  border-radius: 10px;
  padding: 4px 9px;
}

.ipod-value-filter-chip {
  border-radius: 999px;
  border: 1px solid rgba(163, 188, 222, 0.34);
  background-color: rgba(20, 28, 42, 0.85);
  color: #d7e6ff;
  font-size: 11px;
  font-weight: 700;
  padding: 3px 11px;
}

.ipod-value-filter-chip:checked {
  border-color: rgba(121, 183, 255, 0.8);
  background-image: linear-gradient(90deg, rgba(68, 121, 255, 0.4), rgba(110, 189, 255, 0.32));
  color: #f0f7ff;
}

.ipod-value-ops-label {
  color: #9eb2cf;
  font-size: 11px;
  font-weight: 700;
}

.ipod-value-ops-spin {
  min-width: 78px;
}

.ipod-value-ops-status {
  color: #95a6c0;
  font-size: 12px;
  font-weight: 600;
}

.ipod-value-card,
.ipod-value-section {
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background-color: rgba(8, 11, 16, 0.84);
}

.ipod-value-card-title {
  color: #9fb4d6;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.6px;
}

.ipod-value-card-amount {
  color: #f5f9ff;
  font-size: 29px;
  font-weight: 800;
  letter-spacing: -0.3px;
}

.ipod-value-card-low {
  background-image: linear-gradient(145deg, rgba(53, 78, 118, 0.3), rgba(11, 17, 29, 0.82));
}

.ipod-value-card-median {
  background-image: linear-gradient(145deg, rgba(58, 118, 157, 0.35), rgba(12, 23, 34, 0.86));
}

.ipod-value-card-high {
  background-image: linear-gradient(145deg, rgba(90, 120, 188, 0.36), rgba(16, 24, 39, 0.9));
}

.ipod-value-section-title {
  color: #dbe8ff;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.25px;
}

.ipod-value-bar-row {
  margin: 1px 0 1px 0;
}

.ipod-value-bar-label {
  color: #9eb0cb;
  font-size: 12px;
  font-weight: 600;
}

.ipod-value-bar-value {
  color: #dbe7fb;
  font-size: 12px;
  font-weight: 700;
}

.ipod-value-bar > trough {
  min-height: 6px;
  border-radius: 999px;
  background-color: rgba(255, 255, 255, 0.08);
}

.ipod-value-bar progress {
  border-radius: 999px;
  background-image: linear-gradient(90deg, #72a6ff 0%, #9ad2ff 100%);
  transition: 180ms ease-out;
}

.ipod-value-list-row {
  border-radius: 8px;
}

button.ipod-value-list-row {
  background-color: transparent;
  border: 1px solid transparent;
  padding: 3px 5px;
}

button.ipod-value-list-row:hover {
  border-color: rgba(163, 190, 229, 0.3);
  background-color: rgba(34, 45, 64, 0.5);
}

button.ipod-value-list-row.is-highlighted {
  border-color: rgba(121, 183, 255, 0.8);
  background-color: rgba(54, 87, 142, 0.55);
}

.ipod-value-list-label {
  color: #d2def2;
  font-size: 12px;
  font-weight: 600;
}

.ipod-value-detector-group {
  border-radius: 8px;
  margin: 1px 0;
}

.ipod-value-muted {
  color: #8d9ab0;
  font-size: 12px;
}

/* Interactive Value List Styles */
.interactive-value-list {
  background-color: rgba(8, 11, 16, 0.84);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.12);
}

.interactive-list-title {
  color: #f1f6ff;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: -0.3px;
}

.interactive-list-nav {
  color: #9eb2cf;
  font-size: 11px;
  font-weight: 600;
}

.interactive-back-button {
  border-radius: 10px;
  padding: 6px 12px;
  background-image: linear-gradient(145deg, rgba(68, 121, 255, 0.4), rgba(110, 189, 255, 0.32));
  border: 1px solid rgba(121, 183, 255, 0.5);
  color: #f0f7ff;
  font-size: 12px;
  font-weight: 600;
}

.interactive-back-button:hover {
  background-image: linear-gradient(145deg, rgba(68, 121, 255, 0.55), rgba(110, 189, 255, 0.45));
  border-color: rgba(121, 183, 255, 0.7);
}

.interactive-album-button {
  background-color: transparent;
  border: 1px solid transparent;
  border-radius: 10px;
  padding: 0;
  transition: all 150ms ease-out;
}

.interactive-album-button:hover {
  background-color: rgba(34, 45, 64, 0.6);
  border-color: rgba(163, 190, 229, 0.4);
}

.interactive-album-button:active {
  background-color: rgba(68, 121, 255, 0.25);
  border-color: rgba(121, 183, 255, 0.6);
}

.interactive-album-cover {
  color: #7f8ba0;
  opacity: 0.8;
}

.interactive-album-title {
  color: #f1f6ff;
  font-size: 14px;
  font-weight: 600;
  line-height: 1.3;
}

.interactive-album-artist {
  color: #9eb2cf;
  font-size: 12px;
  font-weight: 500;
}

.interactive-album-meta {
  color: #7f8ba0;
  font-size: 11px;
  font-weight: 500;
  margin-top: 2px;
}

.interactive-album-price {
  color: #8be7b2;
  font-size: 14px;
  font-weight: 700;
}

.interactive-album-id {
  color: #5d6d85;
  font-size: 10px;
  font-weight: 500;
}

.interactive-list-empty {
  color: #8d9ab0;
  font-size: 13px;
  font-style: italic;
  padding: 20px;
}

.interactive-album-link {
  border-radius: 999px;
  font-size: 10px;
  font-weight: 700;
}

/* Enhanced Value List Row Styles */
button.ipod-value-list-row {
  background-color: transparent;
  border: 1px solid transparent;
  padding: 6px 8px;
  border-radius: 8px;
  transition: all 120ms ease-out;
}

button.ipod-value-list-row:hover {
  border-color: rgba(163, 190, 229, 0.4);
  background-color: rgba(34, 45, 64, 0.6);
}

button.ipod-value-list-row:active {
  background-color: rgba(68, 121, 255, 0.2);
}

.ipod-value-list-label {
  color: #d2def2;
  font-size: 13px;
  font-weight: 500;
}

button.ipod-value-list-row:hover .ipod-value-list-label {
  color: #ffffff;
}

button.ipod-value-list-row.is-highlighted .ipod-value-list-label {
  color: #ffffff;
}

/* --- Text readability: override GTK dim-label opacity on dark panels --- */
.ipod-panel .dim-label,
.ipod-panel label.dim-label {
  opacity: 1;
  color: #9eadc2;
}

/* Tier 3 data values — market prices, metrics, ratings, stats */
.ipod-detail-data {
  color: #c0cee0;
  font-size: 13px;
  line-height: 1.4;
}

/* Improve title-5 section headings within panels */
.ipod-panel .title-5 {
  color: #d0daea;
  font-weight: 600;
  margin-top: 6px;
}
"""

_SETTING_VALUE_OPS_STALE_DAYS = "gui_value_ops_stale_days"
_SETTING_VALUE_OPS_REFRESH_LIMIT = "gui_value_ops_refresh_limit"
_DEFAULT_VALUE_OPS_STALE_DAYS = 30
_DEFAULT_VALUE_OPS_REFRESH_LIMIT = 10000
_MAX_VALUE_OPS_STALE_DAYS = 3650
_MAX_VALUE_OPS_REFRESH_LIMIT = 100000
_VALUE_DASHBOARD_TOP_LIMIT = 25
_VALUE_DASHBOARD_BOTTOM_LIMIT = 25
_VALUE_DASHBOARD_TREND_LIMIT = 12
_DETAIL_PANEL_WIDTH_RATIO = 0.28
_DETAIL_PANEL_MIN_WIDTH = 200
_DETAIL_PANEL_MAX_WIDTH = 440
_WANTLIST_DETAIL_PANEL_WIDTH_RATIO = 0.24
_WANTLIST_DETAIL_PANEL_MIN_WIDTH = 180
_WANTLIST_DETAIL_PANEL_MAX_WIDTH = 340
_SPLIT_ANIMATION_INTERVAL_MS = 14
_SPLIT_ANIMATION_MIN_STEPS = 6
_SPLIT_ANIMATION_MAX_STEPS = 20
_TRACKLIST_DETAIL_CACHE_LIMIT = 384
_README_DOC_PATH = "README.md"
_PRODUCT_STATE_DOC_PATH = "PRODUCT_STATE.md"
_SPOTIFY_WALKTHROUGH_DOC_PATH = "SPOTIFY_AUTH_CLI_WALKTHROUGH.md"
_SPOTIFY_DASHBOARD_URL = "https://developer.spotify.com/dashboard"
_SPOTIFY_OAUTH_GUIDE_URL = (
    "https://developer.spotify.com/documentation/web-api/tutorials/code-flow"
)
_DISCOGS_TOKEN_URL = "https://www.discogs.com/settings/developers"


def _normalize_release_limit(value: object | None) -> int | None:
    if value is None:
        return None
    limit = _to_int(value)
    if limit <= 0:
        return None
    return limit


def _to_int(value: object | None, *, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped and stripped.lstrip("-").isdigit():
            return int(stripped)
    return default


def _to_float(value: object | None, *, default: float = 0.0) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return default
        try:
            return float(stripped)
        except ValueError:
            return default
    return default


def _as_optional_str(value: object | None) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _as_optional_str_list(value: object | None) -> list[str] | None:
    if not isinstance(value, list):
        return None
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        text = item.strip()
        if text:
            result.append(text)
    return result


def _build_window_header_bar() -> Gtk.HeaderBar:
    header_bar = Gtk.HeaderBar()
    header_bar.set_show_title_buttons(True)
    header_bar.set_decoration_layout(":minimize,maximize,close")
    return header_bar


class MainWindow(Gtk.ApplicationWindow):
    def __init__(
        self,
        app: Adw.Application,
        *,
        limit: int | None = None,
        preload_covers: bool = True,
        on_interactive_highest_navigate: Callable[[int], None] | None = None,
        on_interactive_lowest_navigate: Callable[[int], None] | None = None,
        on_interactive_median_navigate: Callable[[int], None] | None = None,
    ) -> None:
        super().__init__(application=app, title="Discogs Player")
        self.add_css_class("ipod-shell")
        # Set more reasonable minimum size for better UX
        self.set_default_size(1200, 800)  # Slightly smaller for better compatibility
        # Allow a smaller minimum size for better compatibility on small screens
        self.set_size_request(900, 700)
        self.set_resizable(True)
        self.set_deletable(True)
        self.set_titlebar(_build_window_header_bar())
        titlebar = self.get_titlebar()
        if isinstance(titlebar, Gtk.HeaderBar):
            self._install_header_help_menu(titlebar)
        self._setup_help_window: Gtk.Window | None = None
        self._install_css()

        self._limit = _normalize_release_limit(limit)
        self._preload_covers = bool(preload_covers)
        self._selected_release_id: int | None = None
        self._selected_release: dict[str, object] | None = None
        self._visible_release_ids: list[int] = []
        self._visible_release_id_to_index: dict[int, int] = {}
        self._pending_spin_result: dict[str, object] | None = None
        self._release_tracklist_cache: OrderedDict[int, dict[str, object]] = (
            OrderedDict()
        )

        self._selected_wantlist_id: int | None = None
        self._selected_wantlist: dict[str, object] | None = None
        self._visible_wantlist_ids: list[int] = []
        self._visible_wantlist_id_to_index: dict[int, int] = {}
        self._wantlist_tracklist_cache: OrderedDict[int, dict[str, object]] = (
            OrderedDict()
        )
        self._wantlist_syncing_selection = False
        self._wantlist_scroll_accum = 0.0
        self._wantlist_syncing_mode_toggle = False
        self._syncing_selection = False
        self._syncing_mode_toggle = False
        self._scroll_accum = 0.0
        self._split_animation_source_ids: dict[str, int] = {}
        self._actions_executor = ThreadPoolExecutor(
            max_workers=4,
            thread_name_prefix="ui-actions",
        )
        self._inflight_actions: set[str] = set()
        self._value_ops_executor = ThreadPoolExecutor(
            max_workers=2,
            thread_name_prefix="value-dashboard-ops",
        )
        self._value_op_inflight = False
        self._persisting_value_ops_settings = False
        (
            self._value_ops_stale_days,
            self._value_ops_refresh_limit,
        ) = self._load_value_ops_controls_from_settings()
        self._capabilities = get_capabilities()
        self._spotify_capability = self._capabilities.spotify

        # Add window resize handling using notify signals (GTK4 compatible)
        self.connect('notify::default-width', self._on_window_resize)
        self.connect('notify::default-height', self._on_window_resize)
        self.connect('notify::width', self._on_window_resize)
        self.connect('notify::height', self._on_window_resize)
        self.connect('notify::maximized', self._on_window_state_change)
        self.connect('notify::fullscreened', self._on_window_state_change)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.add_css_class("ipod-root")
        self.set_child(root)
        self._root = root

        view_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        view_row.add_css_class("ipod-view-row")
        root.append(view_row)

        view_title = Gtk.Label(label="Section")
        view_title.set_xalign(0.0)
        view_title.add_css_class("ipod-view-title")
        view_row.append(view_title)

        self._main_stack = Gtk.Stack()
        self._main_stack.set_hexpand(True)
        self._main_stack.set_vexpand(True)
        self._main_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._main_stack.connect(
            "notify::visible-child-name", self._handle_main_stack_changed
        )

        self._main_stack_switcher = Gtk.StackSwitcher()
        self._main_stack_switcher.add_css_class("ipod-view-switcher")
        self._main_stack_switcher.set_stack(self._main_stack)
        view_row.append(self._main_stack_switcher)

        self._setup_banner = Adw.Banner()
        self._setup_banner.set_title(
            "Discogs not connected \u2014 connect your account to browse and spin your collection"
        )
        self._setup_banner.set_button_label("Set Up \u2192")
        self._setup_banner.connect("button-clicked", lambda _: self._open_setup_wizard())
        self._setup_banner.set_revealed(False)
        root.append(self._setup_banner)
        root.append(self._main_stack)

        browse_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        browse_page.set_hexpand(True)
        browse_page.set_vexpand(True)
        self._main_stack.add_titled(browse_page, "browse", "Browse")

        wantlist_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        wantlist_page.set_hexpand(True)
        wantlist_page.set_vexpand(True)
        self._main_stack.add_titled(wantlist_page, "wantlist", "Wantlist")

        self._wantlist_filters = WantlistFilterBar(
            default_limit=self._limit,
            on_refresh=self._refresh_wantlist_from_filters,
            on_sync=self._handle_wantlist_sync_clicked,
        )
        self._wantlist_filters.add_css_class("ipod-panel")
        self._wantlist_filters_scroll = Gtk.ScrolledWindow()
        self._wantlist_filters_scroll.set_hexpand(True)
        self._wantlist_filters_scroll.set_vexpand(False)
        self._wantlist_filters_scroll.set_policy(
            Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER
        )
        self._wantlist_filters_scroll.set_child(self._wantlist_filters)
        wantlist_page.append(self._wantlist_filters_scroll)

        wantlist_content = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)
        wantlist_content.set_resize_start_child(True)
        wantlist_content.set_shrink_start_child(True)
        wantlist_content.set_resize_end_child(True)
        wantlist_content.set_shrink_end_child(False)
        wantlist_content.set_wide_handle(True)
        wantlist_content.connect("notify::width", self._on_content_width_change)
        self._wantlist_content = wantlist_content
        wantlist_page.append(wantlist_content)

        wantlist_browser_panel = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=8
        )
        wantlist_browser_panel.set_margin_top(8)
        wantlist_browser_panel.set_margin_bottom(8)
        wantlist_browser_panel.set_margin_start(8)
        wantlist_browser_panel.set_margin_end(8)
        self._wantlist_panel = wantlist_browser_panel
        wantlist_content.set_start_child(wantlist_browser_panel)

        wantlist_mode_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        wantlist_mode_row.add_css_class("ipod-mode-row")
        wantlist_browser_panel.append(wantlist_mode_row)

        wantlist_mode_title = Gtk.Label(label="Browse Mode")
        wantlist_mode_title.set_xalign(0.0)
        wantlist_mode_title.add_css_class("ipod-mode-title")
        wantlist_mode_row.append(wantlist_mode_title)

        self._wantlist_carousel_mode = Gtk.ToggleButton(label="Carousel")
        self._wantlist_carousel_mode.add_css_class("ipod-mode-toggle")
        self._wantlist_carousel_mode.connect(
            "toggled", self._handle_wantlist_carousel_mode_toggled
        )
        wantlist_mode_row.append(self._wantlist_carousel_mode)

        self._wantlist_text_mode = Gtk.ToggleButton(label="Text Menu")
        self._wantlist_text_mode.add_css_class("ipod-mode-toggle")
        self._wantlist_text_mode.connect(
            "toggled", self._handle_wantlist_text_mode_toggled
        )
        wantlist_mode_row.append(self._wantlist_text_mode)

        self._wantlist_gallery_mode = Gtk.ToggleButton(label="Gallery")
        self._wantlist_gallery_mode.add_css_class("ipod-mode-toggle")
        self._wantlist_gallery_mode.connect(
            "toggled", self._handle_wantlist_gallery_mode_toggled
        )
        wantlist_mode_row.append(self._wantlist_gallery_mode)

        wantlist_mode_spacer = Gtk.Box()
        wantlist_mode_spacer.set_hexpand(True)
        wantlist_mode_row.append(wantlist_mode_spacer)

        self._wantlist_spin_wheel = SpinWheel(
            on_spin=self._handle_wantlist_spin_clicked,
            on_play_last_spin=self._handle_wantlist_play_last_spin_clicked,
            compact=True,
        )
        self._wantlist_spin_wheel.set_spotify_capability(
            playback_available=bool(
                self._spotify_capability.addon_available
                and self._spotify_capability.configured
            )
        )
        self._wantlist_spin_wheel.add_css_class("ipod-panel")
        self._wantlist_spin_wheel.add_css_class("ipod-mode-spin")
        wantlist_mode_row.append(self._wantlist_spin_wheel)

        self._wantlist_stack = Gtk.Stack()
        self._wantlist_stack.set_hexpand(True)
        self._wantlist_stack.set_vexpand(True)
        self._wantlist_stack.set_transition_type(
            Gtk.StackTransitionType.SLIDE_LEFT_RIGHT
        )
        self._wantlist_stack.connect("notify::width", self._on_stack_size_change)
        self._wantlist_stack.connect("notify::height", self._on_stack_size_change)

        self._wantlist_empty_box, self._wantlist_empty_label = (
            self._build_empty_state_box(
                "Sync your wantlist to get started.",
                "Sync Wantlist",
                self._handle_wantlist_sync_clicked,
            )
        )
        self._wantlist_empty_box.set_visible(False)
        wantlist_overlay = Gtk.Overlay()
        wantlist_overlay.set_hexpand(True)
        wantlist_overlay.set_vexpand(True)
        wantlist_overlay.set_child(self._wantlist_stack)
        wantlist_overlay.add_overlay(self._wantlist_empty_box)
        wantlist_browser_panel.append(wantlist_overlay)

        wantlist_scroll_controller = Gtk.EventControllerScroll.new(
            Gtk.EventControllerScrollFlags.VERTICAL
            | Gtk.EventControllerScrollFlags.HORIZONTAL
            | Gtk.EventControllerScrollFlags.DISCRETE
        )
        wantlist_scroll_controller.connect("scroll", self._handle_wantlist_scroll)
        self._wantlist_stack.add_controller(wantlist_scroll_controller)

        self._wantlist_text_menu = ReleaseTextMenu(
            on_selection_changed=self._handle_wantlist_selected
        )
        self._wantlist_carousel = CoverCarousel(
            on_selection_changed=self._handle_wantlist_selected
        )
        self._wantlist_gallery = CoverGrid(
            on_selection_changed=self._handle_wantlist_selected,
            on_back_requested=self._handle_wantlist_gallery_back_requested,
        )
        self._wantlist_stack.add_named(self._wantlist_text_menu, "text")
        self._wantlist_stack.add_named(self._wantlist_carousel, "carousel")
        self._wantlist_stack.add_named(self._wantlist_gallery, "gallery")
        self._wantlist_stack.set_visible_child_name("carousel")

        wantlist_sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        wantlist_sidebar.set_valign(Gtk.Align.START)
        wantlist_sidebar.set_margin_top(8)
        wantlist_sidebar.set_margin_bottom(8)
        wantlist_sidebar.set_margin_start(8)
        wantlist_sidebar.set_margin_end(8)
        self._wantlist_sidebar_scroll = Gtk.ScrolledWindow()
        self._wantlist_sidebar_scroll.set_hexpand(False)
        self._wantlist_sidebar_scroll.set_vexpand(True)
        self._wantlist_sidebar_scroll.set_min_content_width(320)
        self._wantlist_sidebar_scroll.set_propagate_natural_width(False)
        self._wantlist_sidebar_scroll.set_propagate_natural_height(False)
        self._wantlist_sidebar_scroll.set_policy(
            Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC
        )
        self._wantlist_sidebar_scroll.set_child(wantlist_sidebar)
        wantlist_content.set_end_child(self._wantlist_sidebar_scroll)

        self._wantlist_detail = WantlistDetail(
            on_auto_match=self._handle_wantlist_auto_match_clicked,
            on_override=self._handle_wantlist_override_clicked,
            on_play=self._handle_wantlist_play_clicked,
            on_refresh_tracklist=self._handle_wantlist_tracklist_refresh_clicked,
            on_refresh_pricing=self._handle_wantlist_pricing_refresh_clicked,
            on_view_market_value=self._handle_wantlist_view_market_value_clicked,
        )
        self._wantlist_detail.set_spotify_capability(
            addon_available=bool(self._spotify_capability.addon_available),
            configured=bool(self._spotify_capability.configured),
            action_label=self._spotify_capability.action_label,
        )
        self._wantlist_detail.add_css_class("ipod-panel")
        wantlist_sidebar.append(self._wantlist_detail)

        self._wantlist_carousel_mode.set_active(True)
        self._set_wantlist_mode("carousel")

        self._filters = FilterBar(
            default_limit=self._limit,
            on_refresh=self._refresh_from_filters,
        )
        self._filters.add_css_class("ipod-panel")
        self._filters.add_css_class("ipod-filter-bar")
        self._filters_scroll = Gtk.ScrolledWindow()
        self._filters_scroll.set_hexpand(True)
        self._filters_scroll.set_vexpand(False)
        self._filters_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        self._filters_scroll.set_child(self._filters)
        browse_page.append(self._filters_scroll)

        content = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)
        content.set_resize_start_child(True)
        content.set_shrink_start_child(True)
        content.set_resize_end_child(True)
        content.set_shrink_end_child(False)
        content.set_wide_handle(True)
        content.connect("notify::width", self._on_content_width_change)
        self._browse_content = content
        browse_page.append(content)

        browser_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        browser_panel.set_margin_top(8)
        browser_panel.set_margin_bottom(8)
        browser_panel.set_margin_start(8)
        browser_panel.set_margin_end(8)
        self._browse_panel = browser_panel
        content.set_start_child(browser_panel)

        mode_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        mode_row.add_css_class("ipod-mode-row")
        browser_panel.append(mode_row)

        mode_title = Gtk.Label(label="Browse Mode")
        mode_title.set_xalign(0.0)
        mode_title.add_css_class("ipod-mode-title")
        mode_row.append(mode_title)

        self._carousel_mode = Gtk.ToggleButton(label="Carousel")
        self._carousel_mode.add_css_class("ipod-mode-toggle")
        self._carousel_mode.connect("toggled", self._handle_carousel_mode_toggled)
        mode_row.append(self._carousel_mode)

        self._text_mode = Gtk.ToggleButton(label="Text Menu")
        self._text_mode.add_css_class("ipod-mode-toggle")
        self._text_mode.connect("toggled", self._handle_text_mode_toggled)
        mode_row.append(self._text_mode)

        self._gallery_mode = Gtk.ToggleButton(label="Gallery")
        self._gallery_mode.add_css_class("ipod-mode-toggle")
        self._gallery_mode.connect("toggled", self._handle_gallery_mode_toggled)
        mode_row.append(self._gallery_mode)

        mode_spacer = Gtk.Box()
        mode_spacer.set_hexpand(True)
        mode_row.append(mode_spacer)

        self._spin_wheel = SpinWheel(
            on_spin=self._handle_spin_clicked,
            on_play_last_spin=self._handle_play_last_spin_clicked,
            compact=True,
        )
        self._spin_wheel.set_spotify_capability(
            playback_available=bool(
                self._spotify_capability.addon_available
                and self._spotify_capability.configured
            )
        )
        self._spin_wheel.add_css_class("ipod-panel")
        self._spin_wheel.add_css_class("ipod-mode-spin")
        mode_row.append(self._spin_wheel)

        self._browse_stack = Gtk.Stack()
        self._browse_stack.set_hexpand(True)
        self._browse_stack.set_vexpand(True)
        self._browse_stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self._browse_stack.connect("notify::width", self._on_stack_size_change)
        self._browse_stack.connect("notify::height", self._on_stack_size_change)

        self._browse_empty_box, self._browse_empty_label = (
            self._build_empty_state_box(
                "Sync your collection to get started.",
                "Sync Collection",
                self._handle_browse_sync_clicked,
            )
        )
        self._browse_empty_box.set_visible(False)
        browse_overlay = Gtk.Overlay()
        browse_overlay.set_hexpand(True)
        browse_overlay.set_vexpand(True)
        browse_overlay.set_child(self._browse_stack)
        browse_overlay.add_overlay(self._browse_empty_box)
        self._browse_ftux_box = self._build_ftux_state_box()
        self._browse_ftux_box.set_visible(False)
        browse_overlay.add_overlay(self._browse_ftux_box)
        browser_panel.append(browse_overlay)
        scroll_controller = Gtk.EventControllerScroll.new(
            Gtk.EventControllerScrollFlags.VERTICAL
            | Gtk.EventControllerScrollFlags.HORIZONTAL
            | Gtk.EventControllerScrollFlags.DISCRETE
        )
        scroll_controller.connect("scroll", self._handle_browse_scroll)
        self._browse_stack.add_controller(scroll_controller)

        self._text_menu = ReleaseTextMenu(
            on_selection_changed=self._handle_release_selected
        )
        self._carousel = CoverCarousel(
            on_selection_changed=self._handle_release_selected
        )
        self._browse_gallery = CoverGrid(
            on_selection_changed=self._handle_release_selected,
            on_back_requested=self._handle_gallery_back_requested,
        )
        self._browse_stack.add_named(self._text_menu, "text")
        self._browse_stack.add_named(self._carousel, "carousel")
        self._browse_stack.add_named(self._browse_gallery, "gallery")
        self._browse_stack.set_visible_child_name("carousel")

        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        sidebar.set_valign(Gtk.Align.START)
        sidebar.set_margin_top(8)
        sidebar.set_margin_bottom(8)
        sidebar.set_margin_start(8)
        sidebar.set_margin_end(8)
        self._sidebar_scroll = Gtk.ScrolledWindow()
        self._sidebar_scroll.set_hexpand(False)
        self._sidebar_scroll.set_vexpand(True)
        self._sidebar_scroll.set_min_content_width(320)
        self._sidebar_scroll.set_propagate_natural_width(False)
        self._sidebar_scroll.set_propagate_natural_height(False)
        self._sidebar_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self._sidebar_scroll.set_child(sidebar)
        content.set_end_child(self._sidebar_scroll)
        # Use a more reasonable position that allows for responsive behavior
        # Set position to 70% of window width or use a responsive approach
        # content.set_position(850)  # Old hardcoded position
        # We'll let the paned handle this dynamically with resize properties

        self._album_detail = AlbumDetail(
            on_auto_match=self._handle_auto_match_clicked,
            on_override=self._handle_override_clicked,
            on_play=self._handle_play_clicked,
            on_match_audit=self._handle_match_audit_clicked,
            on_apply_safe_matches=self._handle_apply_safe_matches_clicked,
            on_review_apply=self._handle_apply_review_queue_clicked,
            on_review_reject=self._handle_reject_review_queue_clicked,
            on_retry_audit_errors=self._handle_retry_audit_errors_clicked,
            on_refresh_tracklist=self._handle_tracklist_refresh_clicked,
            on_view_market_value=self._handle_view_market_value_clicked,
        )
        self._album_detail.set_spotify_capability(
            addon_available=bool(self._spotify_capability.addon_available),
            configured=bool(self._spotify_capability.configured),
            action_label=self._spotify_capability.action_label,
        )
        self._album_detail.set_global_spotify_actions_enabled(True)
        self._album_detail.add_css_class("ipod-panel")
        sidebar.append(self._album_detail)
        self._device_picker = DevicePicker(
            on_refresh=self._handle_devices_refresh_clicked,
            on_set_default=self._handle_set_default_device_clicked,
            on_auto_select=self._handle_auto_select_device_clicked,
        )
        if not self._spotify_capability.addon_available:
            self._device_picker.set_visible(False)
        elif not self._spotify_capability.configured:
            self._device_picker.set_capability_hint(
                "Connect Spotify (`dplayer auth spotify`) to manage devices.",
                show_controls=False,
            )
        else:
            self._device_picker.set_capability_hint(None, show_controls=True)
        self._device_picker.add_css_class("ipod-panel")
        sidebar.append(self._device_picker)

        self._value_dashboard = ValueDashboard(
            on_refresh=self._handle_value_dashboard_refresh,
            on_release_selected=self._handle_value_dashboard_release_selected,
            on_refresh_missing=self._handle_value_refresh_missing_clicked,
            on_refresh_stale=self._handle_value_refresh_stale_clicked,
            on_snapshot_now=self._handle_value_snapshot_clicked,
            on_ops_controls_changed=self._handle_value_ops_controls_changed,
            on_open_docs=self._handle_market_value_docs_requested,
        )
        self._value_dashboard.set_ops_controls(
            stale_days=self._value_ops_stale_days,
            refresh_limit=self._value_ops_refresh_limit,
        )
        self._value_dashboard.add_css_class("ipod-panel")
        self._value_dashboard_scroll = Gtk.ScrolledWindow()
        self._value_dashboard_scroll.set_hexpand(True)
        self._value_dashboard_scroll.set_vexpand(True)
        self._value_dashboard_scroll.set_policy(
            Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC
        )
        self._value_dashboard_scroll.set_child(self._value_dashboard)
        self._main_stack.add_titled(
            self._value_dashboard_scroll, "value", "Market Value"
        )

        self._value_queue_widget = ValueQueueWidget(
            on_refresh=self._handle_value_queue_refresh,
            on_release_selected=self._handle_value_queue_release_selected,
        )
        self._value_queue_widget.add_css_class("ipod-panel")
        self._value_queue_scroll = Gtk.ScrolledWindow()
        self._value_queue_scroll.set_hexpand(True)
        self._value_queue_scroll.set_vexpand(True)
        self._value_queue_scroll.set_policy(
            Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC
        )
        self._value_queue_scroll.set_child(self._value_queue_widget)
        self._main_stack.add_titled(
            self._value_queue_scroll, "queue", "Value Queue"
        )

        self._health_score_widget = HealthScoreWidget(
            on_refresh=self._handle_health_score_refresh,
        )
        self._health_score_widget.add_css_class("ipod-panel")
        self._health_score_scroll = Gtk.ScrolledWindow()
        self._health_score_scroll.set_hexpand(True)
        self._health_score_scroll.set_vexpand(True)
        self._health_score_scroll.set_policy(
            Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC
        )
        self._health_score_scroll.set_child(self._health_score_widget)
        self._main_stack.add_titled(
            self._health_score_scroll, "health", "Health Score"
        )

        self._main_stack.set_visible_child_name("browse")

        initial_status = "Ready."
        if not self._spotify_capability.addon_available:
            initial_status = "Enable Spotify (optional) for playback features."
        elif not self._spotify_capability.configured:
            initial_status = "Connect Spotify to enable playback and auto-match."
        self._status = Gtk.Label(label=initial_status)
        self._status.add_css_class("ipod-status")
        self._status.set_xalign(0.0)
        self._status.set_margin_top(6)
        self._status.set_margin_bottom(8)
        self._status.set_margin_start(12)
        self._status.set_margin_end(12)
        root.append(self._status)

        self._carousel_mode.set_active(True)
        self._set_browse_mode("carousel")

        key_controller = Gtk.EventControllerKey.new()
        key_controller.connect("key-pressed", self._handle_key_pressed)
        self.add_controller(key_controller)

        # Trigger initial data load in background for smooth start
        GLib.idle_add(self._apply_split_layout_from_current_size)
        GLib.timeout_add(120, self._apply_split_layout_from_current_size)
        GLib.idle_add(self._initial_load)

    def _initial_load(self) -> None:
        """Trigger initial data load for both browse and wantlist sections."""
        self.refresh()
        self.refresh_wantlist()

    def do_unroot(self) -> None:  # pragma: no cover - lifecycle callback
        for source_id in self._split_animation_source_ids.values():
            try:
                GLib.source_remove(source_id)
            except Exception:
                pass
        self._split_animation_source_ids.clear()
        self._actions_executor.shutdown(wait=False, cancel_futures=True)
        self._value_ops_executor.shutdown(wait=False, cancel_futures=True)
        super().do_unroot()

    def _refresh_from_filters(self) -> None:
        self.refresh()

    def _refresh_wantlist_from_filters(self) -> None:
        self.refresh_wantlist()

    def refresh(self) -> dict[str, object]:
        filters = self._current_filters()
        result = self.load_releases_with_filters(
            q=filters["q"],  # type: ignore[arg-type]
            year=filters["year"],  # type: ignore[arg-type]
            genres=filters["genres"], # type: ignore[arg-type]
            styles=filters["styles"], # type: ignore[arg-type]
            unmatched=bool(filters["unmatched"]),
            sort_mode=str(filters["sort"]) or "artist_title",
            limit=_normalize_release_limit(filters.get("limit")),
            background=True,
        )
        if self._active_main_view() == "wantlist" and not self._visible_wantlist_ids:
            self.load_wantlist(background=True)
        return result

    def refresh_wantlist(self) -> dict[str, object]:
        """Refresh the wantlist view with current filters."""
        filters = self._current_wantlist_filters()
        result = self.load_wantlist_with_filters(
            q=filters.get("q"),  # type: ignore[arg-type]
            year=filters.get("year"),  # type: ignore[arg-type]
            genres=filters.get("genres"), # type: ignore[arg-type]
            styles=filters.get("styles"), # type: ignore[arg-type]
            sort_mode=str(filters.get("sort")) or "artist_title",
            limit=_normalize_release_limit(filters.get("limit")),
            background=True,
        )
        return result

    def _handle_value_dashboard_refresh(self) -> None:
        self._refresh_value_dashboard(update_status=True)

    def _handle_value_dashboard_release_selected(self, discogs_release_id: int) -> None:
        self._main_stack.set_visible_child_name("browse")
        if self._focus_release_id(discogs_release_id):
            self._set_status(
                f"Focused release {discogs_release_id} from Market Value dashboard."
            )
        else:
            self._set_status(
                f"Release {discogs_release_id} could not be focused from dashboard."
            )

    def _handle_value_queue_refresh(self) -> None:
        self._refresh_value_queue()

    def _handle_value_queue_release_selected(self, discogs_release_id: int) -> None:
        self._main_stack.set_visible_child_name("browse")
        if self._focus_release_id(discogs_release_id):
            self._set_status(
                f"Focused release {discogs_release_id} from Value Queue."
            )
        else:
            self._set_status(
                f"Release {discogs_release_id} could not be focused."
            )

    def _refresh_value_queue(self) -> None:
        self._value_queue_widget.set_busy()
        try:
            report = run_value_refresh_queue()
        except Exception as exc:
            message = self._friendly_error_message(exc)
            self._value_queue_widget.set_error(message)
            self._set_status(f"Value queue unavailable: {message}")
            return
        self._value_queue_widget.set_queue(dict(report))
        total = report.get("total_candidates", 0)
        self._set_status(f"Value queue refreshed ({total} candidate{'s' if total != 1 else ''}).")

    def _handle_health_score_refresh(self) -> None:
        self._refresh_health_score()

    def _refresh_health_score(self) -> None:
        self._health_score_widget.set_busy()
        try:
            report = run_collection_health()
        except Exception as exc:
            message = self._friendly_error_message(exc)
            self._health_score_widget.set_error(message)
            self._set_status(f"Health score unavailable: {message}")
            return
        self._health_score_widget.set_health(dict(report))
        score = report.get("score", 0)
        self._set_status(f"Collection health score: {score}/100.")

    def _load_value_ops_controls_from_settings(self) -> tuple[int, int]:
        stored_stale_days = get_int_setting(
            _SETTING_VALUE_OPS_STALE_DAYS,
            default=_DEFAULT_VALUE_OPS_STALE_DAYS,
        )
        stored_refresh_limit = get_int_setting(
            _SETTING_VALUE_OPS_REFRESH_LIMIT,
            default=_DEFAULT_VALUE_OPS_REFRESH_LIMIT,
        )
        return (
            self._normalize_stale_days(
                stored_stale_days
                if isinstance(stored_stale_days, int)
                else _DEFAULT_VALUE_OPS_STALE_DAYS
            ),
            self._normalize_refresh_limit(
                stored_refresh_limit
                if isinstance(stored_refresh_limit, int)
                else _DEFAULT_VALUE_OPS_REFRESH_LIMIT
            ),
        )

    def _handle_value_ops_controls_changed(self) -> None:
        self._persist_value_ops_controls_to_settings()

    def _persist_value_ops_controls_to_settings(self) -> None:
        if self._persisting_value_ops_settings:
            return
        self._persisting_value_ops_settings = True
        try:
            stale_days = self._normalize_stale_days(self._value_dashboard.stale_days())
            refresh_limit = self._normalize_refresh_limit(
                self._value_dashboard.refresh_limit()
            )
            set_setting(_SETTING_VALUE_OPS_STALE_DAYS, str(stale_days))
            set_setting(_SETTING_VALUE_OPS_REFRESH_LIMIT, str(refresh_limit))
            self._value_ops_stale_days = stale_days
            self._value_ops_refresh_limit = refresh_limit
        finally:
            self._persisting_value_ops_settings = False

    def _handle_value_refresh_missing_clicked(self) -> None:
        stale_days = self._value_dashboard.stale_days()
        refresh_limit = self._value_dashboard.refresh_limit()
        self._start_value_operation(
            op_name="refresh_missing",
            busy_message=(
                f"Refreshing missing market prices (limit {refresh_limit}, "
                f"stale window {stale_days}d)..."
            ),
            runner=lambda: self._run_refresh_missing_operation(
                refresh_limit=refresh_limit,
                stale_days=stale_days,
            ),
        )

    def _handle_value_refresh_stale_clicked(self) -> None:
        stale_days = self._value_dashboard.stale_days()
        refresh_limit = self._value_dashboard.refresh_limit()
        self._start_value_operation(
            op_name="refresh_stale",
            busy_message=(
                f"Refreshing stale market prices ({stale_days}d, "
                f"limit {refresh_limit})..."
            ),
            runner=lambda: self._run_refresh_stale_operation(
                refresh_limit=refresh_limit,
                stale_days=stale_days,
            ),
        )

    def _handle_value_snapshot_clicked(self) -> None:
        self._start_value_operation(
            op_name="snapshot",
            busy_message="Capturing market value snapshot...",
            runner=self._run_snapshot_operation,
        )

    def _start_value_operation(
        self,
        *,
        op_name: str,
        busy_message: str,
        runner: Callable[[], dict[str, object]],
    ) -> None:
        if self._value_op_inflight:
            message = "Market operation already in progress."
            self._value_dashboard.set_ops_busy(message)
            self._set_status(message)
            return

        self._value_op_inflight = True
        self._value_dashboard.set_ops_busy(busy_message)
        self._set_status(busy_message)
        try:
            future = self._value_ops_executor.submit(runner)
        except RuntimeError as exc:
            self._value_op_inflight = False
            message = self._friendly_error_message(exc)
            self._value_dashboard.set_ops_result(
                f"Failed to start operation: {message}"
            )
            self._set_status(message)
            return
        def _on_complete(completed: Future[dict[str, object]]) -> None:
            GLib.idle_add(
                self._complete_value_operation,
                op_name,
                completed,
            )

        future.add_done_callback(_on_complete)

    @staticmethod
    def _normalize_refresh_limit(value: int) -> int:
        return min(max(1, int(value)), _MAX_VALUE_OPS_REFRESH_LIMIT)

    @staticmethod
    def _normalize_stale_days(value: int) -> int:
        return min(max(0, int(value)), _MAX_VALUE_OPS_STALE_DAYS)

    def _run_refresh_missing_operation(
        self,
        *,
        refresh_limit: int,
        stale_days: int,
    ) -> dict[str, object]:
        effective_limit = self._normalize_refresh_limit(refresh_limit)
        effective_stale_days = self._normalize_stale_days(stale_days)
        missing_rows = run_market_value_missing(
            limit=effective_limit,
            stale_days=None,
            with_value=False,
        )
        release_ids = [
            _to_int(item.get("discogs_release_id"))
            for item in missing_rows
            if isinstance(item, dict)
            and isinstance(item.get("discogs_release_id"), int)
        ]
        if not release_ids:
            return {
                "ok": True,
                "operation": "refresh_missing",
                "candidate_count": 0,
                "refreshed_count": 0,
                "priced_count": 0,
                "unpriced_count": 0,
                "error_count": 0,
                "skipped_release_ids": [],
                "warnings": [],
            }
        report = run_refresh_market_values(
            limit=max(1, min(len(release_ids), effective_limit)),
            release_ids=release_ids,
            stale_days=effective_stale_days,
            from_missing=False,
        )
        report["operation"] = "refresh_missing"
        report["refresh_limit"] = effective_limit
        report["stale_days"] = effective_stale_days
        return report

    def _run_refresh_stale_operation(
        self,
        *,
        refresh_limit: int,
        stale_days: int,
    ) -> dict[str, object]:
        effective_limit = self._normalize_refresh_limit(refresh_limit)
        effective_stale_days = self._normalize_stale_days(stale_days)
        report = run_refresh_market_values(
            limit=effective_limit,
            stale_days=effective_stale_days,
            from_missing=False,
        )
        report["operation"] = "refresh_stale"
        report["refresh_limit"] = effective_limit
        report["stale_days"] = effective_stale_days
        return report

    @staticmethod
    def _run_snapshot_operation() -> dict[str, object]:
        report = run_market_value_snapshot()
        report["operation"] = "snapshot"
        return report

    def _complete_value_operation(
        self,
        op_name: str,
        future: Future[dict[str, object]],
    ) -> bool:
        self._value_op_inflight = False
        try:
            report = dict(future.result())
        except Exception as exc:
            message = self._friendly_error_message(exc)
            self._value_dashboard.set_ops_result(f"Market op failed: {message}")
            self._set_status(f"Market op failed: {message}")
            return False

        summary = self._format_value_operation_result(op_name=op_name, report=report)
        self._value_dashboard.set_ops_result(summary)
        self._set_status(summary)
        self._refresh_value_dashboard(update_status=False)
        return False

    @staticmethod
    def _format_value_operation_result(
        *,
        op_name: str,
        report: dict[str, object],
    ) -> str:
        if op_name == "snapshot":
            snapshot_id = _to_int(report.get("snapshot_id"))
            active = _to_int(report.get("active_release_count"))
            priced = _to_int(report.get("priced_release_count"))
            total_median = _to_float(report.get("total_median"))
            return (
                f"Snapshot #{snapshot_id} saved. "
                f"Coverage {priced}/{active}, median total {total_median:,.2f}."
            )

        candidate_count = _to_int(report.get("candidate_count"))
        refreshed_count = _to_int(report.get("refreshed_count"))
        priced_count = _to_int(report.get("priced_count"))
        unpriced_count = _to_int(report.get("unpriced_count"))
        error_count = _to_int(report.get("error_count"))
        refresh_limit = _to_int(report.get("refresh_limit"))
        stale_days = _to_int(report.get("stale_days"))
        if op_name == "refresh_missing":
            label = "Missing refresh"
        elif op_name == "refresh_stale":
            label = "Stale refresh"
        else:
            label = "Market refresh"
        suffix = ""
        if refresh_limit > 0:
            suffix = f" (limit {refresh_limit}, stale {stale_days}d)"
        return (
            f"{label}: candidates {candidate_count}, refreshed {refreshed_count}, "
            f"priced {priced_count}, unpriced {unpriced_count}, errors {error_count}{suffix}."
        )

    def _effective_layout_width(self, width: int) -> int:
        candidate_width = int(width)
        if candidate_width > 1:
            return candidate_width

        window_width = int(self.get_width() or 0)
        if window_width > 1:
            return window_width

        default_width = int(self.get_default_size()[0] or 0)
        return max(default_width, 900)

    def _compute_detail_panel_width(self, width: int, *, wantlist: bool = False) -> int:
        effective_width = self._effective_layout_width(width)
        if wantlist:
            ratio = _WANTLIST_DETAIL_PANEL_WIDTH_RATIO
            min_width = _WANTLIST_DETAIL_PANEL_MIN_WIDTH
            max_width = _WANTLIST_DETAIL_PANEL_MAX_WIDTH
        else:
            ratio = _DETAIL_PANEL_WIDTH_RATIO
            min_width = _DETAIL_PANEL_MIN_WIDTH
            max_width = _DETAIL_PANEL_MAX_WIDTH

        if effective_width <= 1100:
            if wantlist:
                ratio = 0.20
                max_width = 250
            else:
                ratio = 0.22
                max_width = 280
        elif effective_width <= 1400:
            if wantlist:
                ratio = 0.22
                max_width = 300
            else:
                ratio = 0.25
                max_width = 340

        computed = int(effective_width * ratio)
        capped = min(max_width, max(min_width, computed))
        balance_ratio = 0.29 if wantlist else 0.32
        balance_cap = max(min_width, int(effective_width * balance_ratio))
        return min(capped, balance_cap)

    def _clear_split_animation(self, key: str) -> None:
        source_id = self._split_animation_source_ids.pop(str(key), None)
        if source_id is None:
            return
        try:
            GLib.source_remove(source_id)
        except Exception:
            pass

    def _animate_split_position(
        self,
        *,
        key: str,
        paned: Gtk.Paned,
        target_position: int,
    ) -> None:
        target = max(1, int(target_position))
        current = int(paned.get_position() or 0)
        if abs(current - target) <= 2:
            self._clear_split_animation(key)
            paned.set_position(target)
            return

        self._clear_split_animation(key)
        delta = target - current
        steps = max(
            _SPLIT_ANIMATION_MIN_STEPS,
            min(_SPLIT_ANIMATION_MAX_STEPS, max(1, abs(delta) // 36)),
        )

        tick_index = 0

        def _tick() -> bool:
            nonlocal tick_index
            tick_index += 1
            progress = tick_index / float(steps)
            eased = 1.0 - ((1.0 - progress) * (1.0 - progress))
            next_position = current + int(round(delta * eased))
            paned.set_position(max(1, next_position))
            if tick_index >= steps:
                paned.set_position(target)
                self._split_animation_source_ids.pop(key, None)
                return False
            return True

        source_id = GLib.timeout_add(_SPLIT_ANIMATION_INTERVAL_MS, _tick)
        self._split_animation_source_ids[key] = source_id

    def _apply_split_layout(self, width: int) -> None:
        fallback_width = self._effective_layout_width(width)

        if hasattr(self, "_browse_content") and hasattr(self, "_sidebar_scroll"):
            browse_width = self._effective_layout_width(
                self._browse_content.get_width() or fallback_width
            )
            browse_target_detail_width = self._compute_detail_panel_width(browse_width)
            browse_gallery_mode = (
                hasattr(self, "_browse_stack")
                and self._active_browse_mode() == "gallery"
            )
            browse_show_detail = (
                self._browse_gallery.has_active_selection()
                if browse_gallery_mode and hasattr(self, "_browse_gallery")
                else True
            )
            browse_detail_width = (
                browse_target_detail_width if browse_show_detail else 0
            )
            if hasattr(self._sidebar_scroll, "set_max_content_width"):
                self._sidebar_scroll.set_max_content_width(-1)
            self._sidebar_scroll.set_min_content_width(browse_detail_width)
            if hasattr(self._sidebar_scroll, "set_max_content_width"):
                self._sidebar_scroll.set_max_content_width(browse_detail_width)
            self._sidebar_scroll.set_size_request(browse_detail_width, -1)
            if browse_gallery_mode and not browse_show_detail:
                self._sidebar_scroll.set_opacity(0.0)
                self._sidebar_scroll.set_sensitive(False)
            else:
                self._sidebar_scroll.set_opacity(1.0)
                self._sidebar_scroll.set_sensitive(True)

            browse_target_position = max(1, browse_width - browse_detail_width)
            if browse_gallery_mode:
                self._animate_split_position(
                    key="browse",
                    paned=self._browse_content,
                    target_position=browse_target_position,
                )
            else:
                self._clear_split_animation("browse")
                self._browse_content.set_position(browse_target_position)

        if hasattr(self, "_wantlist_content") and hasattr(
            self, "_wantlist_sidebar_scroll"
        ):
            wantlist_width = self._effective_layout_width(
                self._wantlist_content.get_width() or fallback_width
            )
            wantlist_target_detail_width = self._compute_detail_panel_width(
                wantlist_width, wantlist=True
            )
            wantlist_gallery_mode = (
                hasattr(self, "_wantlist_stack")
                and self._active_wantlist_mode() == "gallery"
            )
            wantlist_show_detail = (
                self._wantlist_gallery.has_active_selection()
                if wantlist_gallery_mode and hasattr(self, "_wantlist_gallery")
                else True
            )
            wantlist_detail_width = (
                wantlist_target_detail_width if wantlist_show_detail else 0
            )
            if hasattr(self._wantlist_sidebar_scroll, "set_max_content_width"):
                self._wantlist_sidebar_scroll.set_max_content_width(-1)
            self._wantlist_sidebar_scroll.set_min_content_width(wantlist_detail_width)
            if hasattr(self._wantlist_sidebar_scroll, "set_max_content_width"):
                self._wantlist_sidebar_scroll.set_max_content_width(
                    wantlist_detail_width
                )
            self._wantlist_sidebar_scroll.set_size_request(wantlist_detail_width, -1)
            if wantlist_gallery_mode and not wantlist_show_detail:
                self._wantlist_sidebar_scroll.set_opacity(0.0)
                self._wantlist_sidebar_scroll.set_sensitive(False)
            else:
                self._wantlist_sidebar_scroll.set_opacity(1.0)
                self._wantlist_sidebar_scroll.set_sensitive(True)

            wantlist_target_position = max(1, wantlist_width - wantlist_detail_width)
            if wantlist_gallery_mode:
                self._animate_split_position(
                    key="wantlist",
                    paned=self._wantlist_content,
                    target_position=wantlist_target_position,
                )
            else:
                self._clear_split_animation("wantlist")
                self._wantlist_content.set_position(wantlist_target_position)

        self._sync_carousel_layout_hints()

    def _sync_carousel_layout_hints(self) -> None:
        if hasattr(self, "_carousel") and hasattr(self, "_browse_stack"):
            self._carousel.apply_layout_hint(
                int(self._browse_stack.get_width() or 0),
                int(self._browse_stack.get_height() or 0),
            )
        if hasattr(self, "_wantlist_carousel") and hasattr(self, "_wantlist_stack"):
            self._wantlist_carousel.apply_layout_hint(
                int(self._wantlist_stack.get_width() or 0),
                int(self._wantlist_stack.get_height() or 0),
            )
        if hasattr(self, "_browse_gallery") and hasattr(self, "_browse_stack"):
            self._browse_gallery.apply_layout_hint(
                int(self._browse_stack.get_width() or 0),
                int(self._browse_stack.get_height() or 0),
            )
        if hasattr(self, "_wantlist_gallery") and hasattr(self, "_wantlist_stack"):
            self._wantlist_gallery.apply_layout_hint(
                int(self._wantlist_stack.get_width() or 0),
                int(self._wantlist_stack.get_height() or 0),
            )

    def _on_content_width_change(self, widget: Gtk.Widget, _param) -> None:
        self._apply_split_layout(max(1, int(widget.get_width())))

    def _on_stack_size_change(self, _widget: Gtk.Widget, _param) -> None:
        self._sync_carousel_layout_hints()

    def _on_window_resize(self, window, param) -> None:
        """Handle window resize events for responsive layout adjustments."""
        width = max(1, int(self.get_width()))

        # Update responsive classes on root element
        if hasattr(self, "_root"):
            self._root.remove_css_class("ipod-width-compact")
            self._root.remove_css_class("ipod-width-ultra-compact")
            if width <= 1000:
                self._root.add_css_class("ipod-width-ultra-compact")
            elif width <= 1200:
                self._root.add_css_class("ipod-width-compact")

        self._apply_split_layout(width)

    def _apply_split_layout_from_current_size(self) -> bool:
        self._apply_split_layout(max(1, int(self.get_width())))
        return False

    def _on_window_state_change(self, window, param) -> None:
        """Handle window state changes (maximized, fullscreen, etc.)."""
        # Trigger resize handling when window state changes
        self._on_window_resize(window, param)

    def _build_empty_state_box(
        self,
        label_text: str,
        button_label: str,
        on_click: Callable[[], None],
    ) -> tuple[Gtk.Box, Gtk.Label]:
        """Build a centered empty-state overlay with a descriptive label and action button.

        Returns the outer Box and the Label so callers can update the label text later.
        """
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_halign(Gtk.Align.CENTER)
        box.set_valign(Gtk.Align.CENTER)
        box.add_css_class("ipod-empty-state")
        box.set_can_target(False)  # pass pointer events through to the stack below

        label = Gtk.Label(label=label_text)
        label.set_wrap(True)
        label.set_max_width_chars(48)
        label.set_xalign(0.5)
        label.add_css_class("ipod-empty-state-label")
        box.append(label)

        button = Gtk.Button(label=button_label)
        button.add_css_class("ipod-empty-state-button")
        button.set_can_target(True)  # button itself must be clickable
        button.connect("clicked", lambda _btn: on_click())
        box.append(button)

        return box, label

    def _build_ftux_state_box(self) -> Gtk.Box:
        """Build a rich first-run empty state with icon, heading, and wizard CTA."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        box.set_halign(Gtk.Align.CENTER)
        box.set_valign(Gtk.Align.CENTER)
        box.add_css_class("ipod-ftux-card")
        box.set_can_target(True)

        icon = Gtk.Image.new_from_icon_name("library-music-symbolic")
        icon.set_pixel_size(52)
        icon.add_css_class("ipod-ftux-icon")
        box.append(icon)

        heading = Gtk.Label(label="Welcome to Discogs Spinner")
        heading.add_css_class("ipod-ftux-heading")
        heading.set_xalign(0.5)
        box.append(heading)

        subtitle = Gtk.Label(
            label="Connect your Discogs account to browse and spin your collection."
        )
        subtitle.set_wrap(True)
        subtitle.set_max_width_chars(44)
        subtitle.set_xalign(0.5)
        subtitle.add_css_class("dim-label")
        box.append(subtitle)

        cta = Gtk.Button(label="Set Up Discogs")
        cta.add_css_class("suggested-action")
        cta.add_css_class("ipod-ftux-cta")
        cta.set_halign(Gtk.Align.CENTER)
        cta.set_can_target(True)
        cta.connect("clicked", lambda _: self._open_setup_wizard())
        box.append(cta)

        return box

    def _open_setup_wizard(self) -> None:
        """Instantiate and present the setup wizard, focusing it if already open."""
        existing = getattr(self, "_active_setup_wizard", None)
        if isinstance(existing, SetupWizard) and existing.get_visible():
            existing.present()
            return
        wizard = SetupWizard(self)
        wizard.connect("setup-complete", self._on_wizard_complete)
        wizard.connect("close-request", self._on_wizard_closed)
        wizard.present()
        self._active_setup_wizard: SetupWizard | None = wizard

    def _on_wizard_closed(self, _wizard: object) -> bool:
        self._active_setup_wizard = None
        return False

    def _update_setup_state(self, *, token_missing: bool) -> None:
        """Show or hide FTUX surfaces based on whether the Discogs token is set."""
        self._setup_banner.set_revealed(token_missing)
        if hasattr(self, "_browse_ftux_box"):
            self._browse_ftux_box.set_visible(token_missing)

    def _make_sync_progress_callback(
        self, label: str = "Syncing"
    ) -> Callable[[int, int, int, int], None]:
        """Return a progress callback that posts status updates to the main thread."""

        def _progress(
            page: int, pages: int, _num_items: int, total_items: int
        ) -> None:
            msg = f"{label}... page {page} of {pages} ({total_items} found)"
            GLib.idle_add(self._set_status, msg)

        return _progress

    def _install_css(self) -> None:
        display = self.get_display()
        if display is None:
            return
        provider = Gtk.CssProvider()
        provider.load_from_data(_IPOD_NANO_CSS.encode("utf-8"))
        Gtk.StyleContext.add_provider_for_display(
            display,
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    @staticmethod
    def _project_root() -> Path:
        return Path(__file__).resolve().parents[3]

    def _project_doc_uri(self, relative_path: str) -> str | None:
        normalized = str(relative_path or "").strip()
        if not normalized:
            return None
        try:
            candidate = (self._project_root() / normalized).resolve()
        except Exception:
            return None
        if not candidate.exists() or not candidate.is_file():
            return None
        return candidate.as_uri()

    def _open_project_doc(
        self,
        relative_path: str,
        *,
        fallback_url: str | None = None,
        label: str,
    ) -> None:
        uri = self._project_doc_uri(relative_path)
        if uri and self._open_spotify_url(uri):
            self._set_status(f"Opened {label}.")
            return
        fallback = str(fallback_url or "").strip()
        if fallback and self._open_spotify_url(fallback):
            self._set_status(f"Opened {label} fallback URL.")
            return
        self._set_status(f"{label} is unavailable in this installation.")

    def _install_header_help_menu(self, header_bar: Gtk.HeaderBar) -> None:
        help_button = Gtk.MenuButton()
        if hasattr(help_button, "set_icon_name"):
            help_button.set_icon_name("help-browser-symbolic")
        else:
            help_button.set_label("Help")
        help_button.add_css_class("ipod-help-menu-button")
        help_button.set_tooltip_text("Help, docs, and setup links")

        popover = Gtk.Popover()
        popover_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        popover_box.set_margin_top(10)
        popover_box.set_margin_bottom(10)
        popover_box.set_margin_start(10)
        popover_box.set_margin_end(10)

        def _add_action(label: str, callback: Callable[[], None]) -> None:
            action = Gtk.Button(label=label)
            action.set_halign(Gtk.Align.FILL)
            action.set_hexpand(True)
            action.connect("clicked", lambda *_: callback())
            popover_box.append(action)

        _add_action("Preferences", self._show_preferences_window)
        _add_action(
            "Open README",
            lambda: self._open_project_doc(
                _README_DOC_PATH, label="README", fallback_url=None
            ),
        )
        _add_action(
            "Open Product State",
            lambda: self._open_project_doc(
                _PRODUCT_STATE_DOC_PATH, label="Product State", fallback_url=None
            ),
        )
        _add_action(
            "Open Spotify Walkthrough",
            lambda: self._open_project_doc(
                _SPOTIFY_WALKTHROUGH_DOC_PATH,
                label="Spotify walkthrough",
                fallback_url=_SPOTIFY_OAUTH_GUIDE_URL,
            ),
        )
        _add_action("Setup Commands", self._show_setup_commands_window)
        _add_action(
            "Spotify Dashboard",
            lambda: self._open_project_doc(
                "",
                label="Spotify dashboard",
                fallback_url=_SPOTIFY_DASHBOARD_URL,
            ),
        )
        _add_action(
            "Discogs Token Page",
            lambda: self._open_project_doc(
                "",
                label="Discogs token page",
                fallback_url=_DISCOGS_TOKEN_URL,
            ),
        )

        popover.set_child(popover_box)
        help_button.set_popover(popover)
        header_bar.pack_end(help_button)
        self._help_menu_button = help_button

    @staticmethod
    def _setup_commands_text() -> str:
        return "\n".join(
            [
                "Core setup:",
                "  dplayer setup",
                "  dplayer sync",
                "",
                "Spotify setup:",
                "  dplayer auth spotify-doctor",
                "  dplayer auth spotify --open-browser --listen-host 127.0.0.1 --listen-port 8765",
                "  dplayer devices --json",
                "",
                "Useful URLs:",
                f"  Discogs token page: {_DISCOGS_TOKEN_URL}",
                f"  Spotify dashboard: {_SPOTIFY_DASHBOARD_URL}",
                f"  Spotify OAuth guide: {_SPOTIFY_OAUTH_GUIDE_URL}",
            ]
        )

    def _show_setup_commands_window(self) -> None:
        existing = getattr(self, "_setup_help_window", None)
        if isinstance(existing, Gtk.Window):
            existing.present()
            return

        window = Gtk.Window(title="Setup Commands")
        window.set_transient_for(self)
        window.set_modal(True)
        window.set_default_size(680, 460)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        root.set_margin_top(12)
        root.set_margin_bottom(12)
        root.set_margin_start(12)
        root.set_margin_end(12)

        intro = Gtk.Label(
            label="Run these commands in a terminal to configure Discogs + Spotify."
        )
        intro.set_xalign(0.0)
        intro.set_wrap(True)
        root.append(intro)

        commands_label = Gtk.Label(label=self._setup_commands_text())
        commands_label.set_xalign(0.0)
        commands_label.set_yalign(0.0)
        commands_label.set_wrap(True)
        commands_label.set_selectable(True)
        commands_label.add_css_class("monospace")

        scroll = Gtk.ScrolledWindow()
        scroll.set_hexpand(True)
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_child(commands_label)
        root.append(scroll)

        button_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        close_button = Gtk.Button(label="Close")
        close_button.connect("clicked", lambda *_: window.close())
        button_row.append(close_button)
        root.append(button_row)

        window.set_child(root)

        def _handle_close_request(*_args) -> bool:
            self._setup_help_window = None
            return False

        window.connect("close-request", _handle_close_request)
        self._setup_help_window = window
        window.present()
        self._set_status("Opened setup commands window.")

    def _show_preferences_window(self) -> None:
        prefs = PreferencesWindow(self)
        prefs.present()

    def _check_first_run(self) -> None:
        """Show the setup wizard and FTUX surfaces if Discogs is not yet configured."""
        from discogs_player.use_cases.setup_report import run_setup_report

        try:
            report = run_setup_report()
        except Exception:
            return
        stage = report.get("onboarding_stage")
        if stage == "needs_discogs_token":
            self._update_setup_state(token_missing=True)
            self._open_setup_wizard()

    def _on_wizard_complete(self, _wizard: object) -> None:
        token_missing = not bool(get_discogs_token())
        self._update_setup_state(token_missing=token_missing)
        self.load_releases(background=True)

    def _focus_value_dashboard_release(self, discogs_release_id: int, *, source: str) -> None:
        self._main_stack.set_visible_child_name("value")
        highlighted = self._value_dashboard.highlight_release(discogs_release_id)
        if highlighted:
            self._set_status(
                f"Focused release {discogs_release_id} in Market Value dashboard ({source})."
            )
            return
        self._set_status(
            f"Opened Market Value dashboard for release {discogs_release_id} ({source}); release is not in current dashboard rows."
        )

    def _handle_view_market_value_clicked(self) -> None:
        release_id = self._selected_release_id
        if not isinstance(release_id, int):
            self._set_status("Select a release first.")
            return
        self._focus_value_dashboard_release(release_id, source="browse detail")

    def _handle_wantlist_view_market_value_clicked(self) -> None:
        release_id = self._selected_wantlist_id
        if not isinstance(release_id, int):
            self._set_status("Select a wantlist item first.")
            return
        self._focus_value_dashboard_release(release_id, source="wantlist detail")

    def _handle_market_value_docs_requested(self) -> None:
        self._open_project_doc(
            _README_DOC_PATH,
            label="README",
            fallback_url=_SPOTIFY_OAUTH_GUIDE_URL,
        )

    def _set_browse_mode(self, mode: str) -> None:
        previous_mode = self._active_browse_mode()
        self._syncing_mode_toggle = True
        try:
            if mode == "text":
                self._text_mode.set_active(True)
                self._carousel_mode.set_active(False)
                self._gallery_mode.set_active(False)
                self._browse_stack.set_visible_child_name("text")
                if self._selected_release_id is None and self._visible_release_ids:
                    self._focus_release_id(
                        self._visible_release_ids[0], allow_expand_limit=False
                    )
            elif mode == "carousel":
                self._carousel_mode.set_active(True)
                self._text_mode.set_active(False)
                self._gallery_mode.set_active(False)
                self._browse_stack.set_visible_child_name("carousel")
                if self._selected_release_id is None and self._visible_release_ids:
                    self._focus_release_id(
                        self._visible_release_ids[0], allow_expand_limit=False
                    )
            elif mode == "gallery":
                self._gallery_mode.set_active(True)
                self._carousel_mode.set_active(False)
                self._text_mode.set_active(False)
                self._browse_stack.set_visible_child_name("gallery")
                if previous_mode != "gallery":
                    self._browse_gallery.clear_selection(emit=False)
                    if self._selected_release_id is not None:
                        self._handle_release_selected(None)
        finally:
            self._syncing_mode_toggle = False
        GLib.idle_add(self._apply_split_layout_from_current_size)

    def _set_wantlist_mode(self, mode: str) -> None:
        previous_mode = self._active_wantlist_mode()
        self._wantlist_syncing_mode_toggle = True
        try:
            if mode == "text":
                self._wantlist_text_mode.set_active(True)
                self._wantlist_carousel_mode.set_active(False)
                self._wantlist_gallery_mode.set_active(False)
                self._wantlist_stack.set_visible_child_name("text")
                if self._selected_wantlist_id is None and self._visible_wantlist_ids:
                    self._focus_wantlist_id(
                        self._visible_wantlist_ids[0], allow_expand_limit=False
                    )
            elif mode == "carousel":
                self._wantlist_carousel_mode.set_active(True)
                self._wantlist_text_mode.set_active(False)
                self._wantlist_gallery_mode.set_active(False)
                self._wantlist_stack.set_visible_child_name("carousel")
                if self._selected_wantlist_id is None and self._visible_wantlist_ids:
                    self._focus_wantlist_id(
                        self._visible_wantlist_ids[0], allow_expand_limit=False
                    )
            elif mode == "gallery":
                self._wantlist_gallery_mode.set_active(True)
                self._wantlist_carousel_mode.set_active(False)
                self._wantlist_text_mode.set_active(False)
                self._wantlist_stack.set_visible_child_name("gallery")
                if previous_mode != "gallery":
                    self._wantlist_gallery.clear_selection(emit=False)
                    if self._selected_wantlist_id is not None:
                        self._handle_wantlist_selected(None)
        finally:
            self._wantlist_syncing_mode_toggle = False
        GLib.idle_add(self._apply_split_layout_from_current_size)

    def _handle_wantlist_text_mode_toggled(self, button: Gtk.ToggleButton) -> None:
        if self._wantlist_syncing_mode_toggle:
            return
        if not button.get_active():
            if (
                not self._wantlist_carousel_mode.get_active()
                and not self._wantlist_gallery_mode.get_active()
            ):
                self._set_wantlist_mode("text")
                self._set_wantlist_mode_status("text")
            return
        self._set_wantlist_mode("text")
        self._set_wantlist_mode_status("text")

    def _handle_wantlist_carousel_mode_toggled(self, button: Gtk.ToggleButton) -> None:
        if self._wantlist_syncing_mode_toggle:
            return
        if not button.get_active():
            if (
                not self._wantlist_text_mode.get_active()
                and not self._wantlist_gallery_mode.get_active()
            ):
                self._set_wantlist_mode("carousel")
                self._set_wantlist_mode_status("carousel")
            return
        self._set_wantlist_mode("carousel")
        self._set_wantlist_mode_status("carousel")

    def _handle_wantlist_gallery_mode_toggled(self, button: Gtk.ToggleButton) -> None:
        if self._wantlist_syncing_mode_toggle:
            return
        if not button.get_active():
            if (
                not self._wantlist_text_mode.get_active()
                and not self._wantlist_carousel_mode.get_active()
            ):
                self._set_wantlist_mode("gallery")
                self._set_wantlist_mode_status("gallery")
            return
        self._set_wantlist_mode("gallery")
        self._set_wantlist_mode_status("gallery")

    def _handle_text_mode_toggled(self, button: Gtk.ToggleButton) -> None:
        if self._syncing_mode_toggle:
            return
        if not button.get_active():
            if not self._carousel_mode.get_active() and not self._gallery_mode.get_active():
                self._set_browse_mode("text")
                self._set_browse_mode_status("text")
            return
        self._set_browse_mode("text")
        self._set_browse_mode_status("text")

    def _handle_carousel_mode_toggled(self, button: Gtk.ToggleButton) -> None:
        if self._syncing_mode_toggle:
            return
        if not button.get_active():
            if not self._text_mode.get_active() and not self._gallery_mode.get_active():
                self._set_browse_mode("carousel")
                self._set_browse_mode_status("carousel")
            return
        self._set_browse_mode("carousel")
        self._set_browse_mode_status("carousel")

    def _handle_gallery_mode_toggled(self, button: Gtk.ToggleButton) -> None:
        if self._syncing_mode_toggle:
            return
        if not button.get_active():
            if not self._text_mode.get_active() and not self._carousel_mode.get_active():
                self._set_browse_mode("gallery")
                self._set_browse_mode_status("gallery")
            return
        self._set_browse_mode("gallery")
        self._set_browse_mode_status("gallery")

    def _handle_gallery_back_requested(self) -> None:
        if self._active_main_view() == "browse":
            GLib.idle_add(self._apply_split_layout_from_current_size)

    def _handle_wantlist_gallery_back_requested(self) -> None:
        if self._active_main_view() == "wantlist":
            GLib.idle_add(self._apply_split_layout_from_current_size)

    def _set_status(self, message: str) -> None:
        if hasattr(self, "_status"):
            self._status.set_text(message)

    def _active_main_view(self) -> str:
        """Get the currently active main view (browse, wantlist, or value)."""
        visible = self._main_stack.get_visible_child_name()
        return str(visible or "browse")

    def _current_filters(self) -> dict[str, object]:
        """Get current browse filters from the filter bar."""
        return self._filters.current_filters()

    def _current_wantlist_filters(self) -> dict[str, object]:
        """Get current wantlist filters from the wantlist filter bar."""
        return self._wantlist_filters.current_filters()

    def _handle_main_stack_changed(self, _stack, _param) -> None:
        """Handle main stack visible child changes."""
        # Skip if still initializing (attributes may not exist yet)
        if not hasattr(self, '_status'):
            return

        active_view = self._active_main_view()
        # Update status to reflect the current view
        if active_view == "browse":
            self._set_status("Switched to Browse view")
            if not self._visible_release_ids:
                self.refresh()
        elif active_view == "wantlist":
            self._set_status("Switched to Wantlist view")
            if not self._visible_wantlist_ids:
                self.refresh_wantlist()
        elif active_view == "value":
            self._set_status("Switched to Market Value view")
        elif active_view == "queue":
            self._set_status("Switched to Value Queue view")
        elif active_view == "health":
            self._set_status("Switched to Health Score view")

        # Reapply responsive split sizing when tabs change so hidden paned widgets
        # don't keep stale allocations from previous visibility states.
        GLib.idle_add(self._apply_split_layout_from_current_size)
        GLib.timeout_add(120, self._apply_split_layout_from_current_size)

    def _active_browse_mode(self) -> str:
        visible = self._browse_stack.get_visible_child_name()
        return str(visible or "carousel")

    def _active_wantlist_mode(self) -> str:
        visible = self._wantlist_stack.get_visible_child_name()
        return str(visible or "carousel")

    @staticmethod
    def _browse_mode_status_text(mode: str) -> str:
        if mode == "text":
            return "Browse mode: Text Menu"
        if mode == "gallery":
            return "Browse mode: Gallery"
        return "Browse mode: Carousel"

    @staticmethod
    def _wantlist_mode_status_text(mode: str) -> str:
        if mode == "text":
            return "Wantlist mode: Text Menu"
        if mode == "gallery":
            return "Wantlist mode: Gallery"
        return "Wantlist mode: Carousel"

    def _set_browse_mode_status(self, mode: str) -> None:
        self._set_status(self._browse_mode_status_text(mode))

    def _set_wantlist_mode_status(self, mode: str) -> None:
        self._set_status(self._wantlist_mode_status_text(mode))

    def _toggle_browse_mode(self) -> None:
        mode = self._active_browse_mode()
        if mode == "carousel":
            self._set_browse_mode("text")
            self._set_browse_mode_status("text")
        elif mode == "text":
            self._set_browse_mode("gallery")
            self._set_browse_mode_status("gallery")
        else:
            self._set_browse_mode("carousel")
            self._set_browse_mode_status("carousel")

    def _toggle_wantlist_mode(self) -> None:
        mode = self._active_wantlist_mode()
        if mode == "carousel":
            self._set_wantlist_mode("text")
            self._set_wantlist_mode_status("text")
        elif mode == "text":
            self._set_wantlist_mode("gallery")
            self._set_wantlist_mode_status("gallery")
        else:
            self._set_wantlist_mode("carousel")
            self._set_wantlist_mode_status("carousel")

    @staticmethod
    def _build_id_index_map(ids: list[int]) -> dict[int, int]:
        index_by_id: dict[int, int] = {}
        for index, release_id in enumerate(ids):
            index_by_id.setdefault(int(release_id), int(index))
        return index_by_id

    def _navigate_selection(
        self, delta: int, *, anchor_first_when_unselected: bool = False
    ) -> None:
        if not self._visible_release_ids:
            return

        current_index: int | None = None
        if isinstance(self._selected_release_id, int):
            current_index = self._visible_release_id_to_index.get(
                int(self._selected_release_id)
            )
        if current_index is not None:
            next_index = (current_index + int(delta)) % len(self._visible_release_ids)
        else:
            if anchor_first_when_unselected:
                next_index = 0
            else:
                current_index = 0
                next_index = (current_index + int(delta)) % len(self._visible_release_ids)
        target_release_id = self._visible_release_ids[next_index]

        # Focus immediately to avoid idle-queue churn during rapid navigation.
        self._focus_release_id(target_release_id, allow_expand_limit=False)

    def _navigate_wantlist_selection(
        self, delta: int, *, anchor_first_when_unselected: bool = False
    ) -> None:
        if not self._visible_wantlist_ids:
            return

        current_index: int | None = None
        if isinstance(self._selected_wantlist_id, int):
            current_index = self._visible_wantlist_id_to_index.get(
                int(self._selected_wantlist_id)
            )
        if current_index is not None:
            next_index = (current_index + int(delta)) % len(self._visible_wantlist_ids)
        else:
            if anchor_first_when_unselected:
                next_index = 0
            else:
                current_index = 0
                next_index = (current_index + int(delta)) % len(self._visible_wantlist_ids)
        target_release_id = self._visible_wantlist_ids[next_index]

        # Focus immediately to avoid idle-queue churn during rapid navigation.
        self._focus_wantlist_id(target_release_id, allow_expand_limit=False)

    def _focused_widget_is_text_input(self) -> bool:
        focus = self.get_focus()
        return isinstance(
            focus, (Gtk.Entry, Gtk.SpinButton, Gtk.TextView, Gtk.DropDown)
        )

    @staticmethod
    def _is_descendant_of(
        widget: Gtk.Widget | None, ancestor: Gtk.Widget | None
    ) -> bool:
        if widget is None or ancestor is None:
            return False
        current: Gtk.Widget | None = widget
        while current is not None:
            if current is ancestor:
                return True
            current = current.get_parent()
        return False

    def _handle_key_pressed(
        self,
        _controller: Gtk.EventControllerKey,
        keyval: int,
        _keycode: int,
        _state: Gdk.ModifierType,
    ) -> bool:
        active_view = self._active_main_view()
        if active_view not in {"browse", "wantlist"}:
            return False

        panel = self._browse_panel if active_view == "browse" else self._wantlist_panel
        focus = self.get_focus()
        if focus is not None and not self._is_descendant_of(focus, panel):
            return False
        if self._focused_widget_is_text_input():
            return False

        if active_view == "browse" and self._active_browse_mode() == "gallery":
            gallery_columns = max(1, self._browse_gallery.current_columns())
            if keyval in (Gdk.KEY_Left, Gdk.KEY_KP_Left):
                self._navigate_selection(-1, anchor_first_when_unselected=True)
                return True
            if keyval in (Gdk.KEY_Right, Gdk.KEY_KP_Right):
                self._navigate_selection(1, anchor_first_when_unselected=True)
                return True
            if keyval in (Gdk.KEY_Up, Gdk.KEY_KP_Up):
                self._navigate_selection(
                    -gallery_columns, anchor_first_when_unselected=True
                )
                return True
            if keyval in (Gdk.KEY_Down, Gdk.KEY_KP_Down):
                self._navigate_selection(
                    gallery_columns, anchor_first_when_unselected=True
                )
                return True

        if active_view == "wantlist" and self._active_wantlist_mode() == "gallery":
            gallery_columns = max(1, self._wantlist_gallery.current_columns())
            if keyval in (Gdk.KEY_Left, Gdk.KEY_KP_Left):
                self._navigate_wantlist_selection(
                    -1, anchor_first_when_unselected=True
                )
                return True
            if keyval in (Gdk.KEY_Right, Gdk.KEY_KP_Right):
                self._navigate_wantlist_selection(
                    1, anchor_first_when_unselected=True
                )
                return True
            if keyval in (Gdk.KEY_Up, Gdk.KEY_KP_Up):
                self._navigate_wantlist_selection(
                    -gallery_columns, anchor_first_when_unselected=True
                )
                return True
            if keyval in (Gdk.KEY_Down, Gdk.KEY_KP_Down):
                self._navigate_wantlist_selection(
                    gallery_columns, anchor_first_when_unselected=True
                )
                return True

        if keyval in (Gdk.KEY_Up, Gdk.KEY_KP_Up, Gdk.KEY_Left, Gdk.KEY_KP_Left):
            if active_view == "wantlist":
                self._navigate_wantlist_selection(-1)
            else:
                self._navigate_selection(-1)
            return True
        if keyval in (Gdk.KEY_Down, Gdk.KEY_KP_Down, Gdk.KEY_Right, Gdk.KEY_KP_Right):
            if active_view == "wantlist":
                self._navigate_wantlist_selection(1)
            else:
                self._navigate_selection(1)
            return True
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            if active_view == "wantlist":
                self._toggle_wantlist_mode()
            else:
                self._toggle_browse_mode()
            return True
        return False

    def _handle_browse_scroll(
        self,
        _controller: Gtk.EventControllerScroll,
        dx: float,
        dy: float,
    ) -> bool:
        if self._active_browse_mode() == "gallery":
            return False
        # Wheel/trackpad movement is thresholded to one step per logical notch.
        axis_delta = dy if abs(dy) >= abs(dx) else dx
        if axis_delta == 0:
            return False

        self._scroll_accum += float(axis_delta)
        moved = False
        while self._scroll_accum >= 1.0:
            self._navigate_selection(1)
            self._scroll_accum -= 1.0
            moved = True
        while self._scroll_accum <= -1.0:
            self._navigate_selection(-1)
            self._scroll_accum += 1.0
            moved = True
        return moved

    def _handle_wantlist_scroll(
        self,
        _controller: Gtk.EventControllerScroll,
        dx: float,
        dy: float,
    ) -> bool:
        if self._active_wantlist_mode() == "gallery":
            return False
        axis_delta = dy if abs(dy) >= abs(dx) else dx
        if axis_delta == 0:
            return False

        self._wantlist_scroll_accum += float(axis_delta)
        moved = False
        while self._wantlist_scroll_accum >= 1.0:
            self._navigate_wantlist_selection(1)
            self._wantlist_scroll_accum -= 1.0
            moved = True
        while self._wantlist_scroll_accum <= -1.0:
            self._navigate_wantlist_selection(-1)
            self._wantlist_scroll_accum += 1.0
            moved = True
        return moved

    def _sync_release_selection(self, discogs_release_id: int) -> None:
        if self._syncing_selection:
            return
        self._syncing_selection = True
        try:
            self._text_menu.select_release(discogs_release_id)
            self._carousel.select_release(discogs_release_id)
            if self._active_browse_mode() == "gallery":
                self._browse_gallery.select_release(discogs_release_id)
        finally:
            self._syncing_selection = False

    def _sync_wantlist_selection(self, discogs_release_id: int) -> None:
        if self._wantlist_syncing_selection:
            return
        self._wantlist_syncing_selection = True
        try:
            self._wantlist_text_menu.select_release(discogs_release_id)
            self._wantlist_carousel.select_release(discogs_release_id)
            if self._active_wantlist_mode() == "gallery":
                self._wantlist_gallery.select_release(discogs_release_id)
        finally:
            self._wantlist_syncing_selection = False

    @staticmethod
    def _empty_tracklist_payload() -> dict[str, object]:
        return {
            "tracks": [],
            "track_count": 0,
            "audio_track_count": 0,
            "tracklist_last_refreshed_at": None,
            "has_cached_tracklist": False,
            "has_tracklist": False,
            "has_audio_tracks": False,
        }

    @staticmethod
    def _clone_tracklist_payload(payload: dict[str, object]) -> dict[str, object]:
        cloned = dict(payload)
        tracks = payload.get("tracks")
        cloned["tracks"] = (
            [dict(row) for row in tracks if isinstance(row, dict)]
            if isinstance(tracks, list)
            else []
        )
        return cloned

    def _normalize_tracklist_payload(self, payload: dict[str, object]) -> dict[str, object]:
        normalized = self._clone_tracklist_payload(payload)
        tracks = normalized.get("tracks")
        track_count = _to_int(normalized.get("track_count"))
        audio_track_count = _to_int(normalized.get("audio_track_count"))
        last_refreshed = normalized.get("tracklist_last_refreshed_at")
        if last_refreshed is None:
            last_refreshed = normalized.get("last_refreshed_at")
        return {
            "tracks": tracks,
            "track_count": track_count,
            "audio_track_count": audio_track_count,
            "tracklist_last_refreshed_at": last_refreshed,
            "has_cached_tracklist": bool(normalized.get("has_cached_tracklist"))
            or bool(tracks),
            "has_tracklist": bool(normalized.get("has_tracklist")) or track_count > 0,
            "has_audio_tracks": bool(normalized.get("has_audio_tracks"))
            or audio_track_count > 0,
        }

    def _tracklist_cache_get(
        self,
        cache: OrderedDict[int, dict[str, object]],
        *,
        release_id: int,
    ) -> dict[str, object] | None:
        cached = cache.get(release_id)
        if not isinstance(cached, dict):
            return None
        cache.move_to_end(release_id)
        return self._clone_tracklist_payload(cached)

    def _tracklist_cache_put(
        self,
        cache: OrderedDict[int, dict[str, object]],
        *,
        release_id: int,
        payload: dict[str, object],
    ) -> None:
        cache[release_id] = self._normalize_tracklist_payload(payload)
        cache.move_to_end(release_id)
        while len(cache) > _TRACKLIST_DETAIL_CACHE_LIMIT:
            cache.popitem(last=False)

    @staticmethod
    def _tracklist_cache_invalidate(
        cache: OrderedDict[int, dict[str, object]],
        *,
        release_id: int,
    ) -> None:
        cache.pop(release_id, None)

    def _release_with_cached_tracklist(
        self, item: dict[str, object]
    ) -> dict[str, object]:
        release_id = item.get("discogs_release_id")
        enriched = dict(item)
        if not isinstance(release_id, int):
            enriched.update(self._empty_tracklist_payload())
            return enriched

        cached = self._tracklist_cache_get(
            self._release_tracklist_cache,
            release_id=release_id,
        )
        if cached is None:
            try:
                fetched = run_release_tracklist_cached(release_id)
            except Exception:
                fetched = self._empty_tracklist_payload()
            cached = self._normalize_tracklist_payload(fetched)
            self._tracklist_cache_put(
                self._release_tracklist_cache,
                release_id=release_id,
                payload=cached,
            )

        enriched.update(cached)
        return enriched

    def _wantlist_with_cached_tracklist(
        self, item: dict[str, object]
    ) -> dict[str, object]:
        release_id = item.get("discogs_release_id")
        enriched = dict(item)
        if not isinstance(release_id, int):
            enriched.update(self._empty_tracklist_payload())
            return enriched

        cached = self._tracklist_cache_get(
            self._wantlist_tracklist_cache,
            release_id=release_id,
        )
        if cached is None:
            try:
                fetched = run_wantlist_tracklist_cached(release_id)
            except Exception:
                fetched = self._empty_tracklist_payload()
            cached = self._normalize_tracklist_payload(fetched)
            self._tracklist_cache_put(
                self._wantlist_tracklist_cache,
                release_id=release_id,
                payload=cached,
            )

        enriched.update(cached)
        return enriched

    def _set_value_dashboard_from_report(
        self,
        report: dict[str, object],
        *,
        update_status: bool,
    ) -> None:
        self._value_dashboard.set_dashboard(report)
        if not update_status:
            return
        coverage_raw = report.get("coverage")
        coverage = dict(coverage_raw) if isinstance(coverage_raw, dict) else {}
        priced_count = _to_int(coverage.get("priced_release_count"))
        active_count = _to_int(coverage.get("active_release_count"))
        self._set_status(
            f"Market value dashboard refreshed ({priced_count}/{active_count} priced releases)."
        )

    def _refresh_value_dashboard(
        self, *, update_status: bool
    ) -> dict[str, object] | None:
        try:
            report = run_market_value_dashboard(
                top_limit=_VALUE_DASHBOARD_TOP_LIMIT,
                bottom_limit=_VALUE_DASHBOARD_BOTTOM_LIMIT,
                trend_limit=_VALUE_DASHBOARD_TREND_LIMIT,
            )
        except Exception as exc:
            message = self._friendly_error_message(exc)
            self._value_dashboard.set_error(message)
            if update_status:
                self._set_status(f"Market value dashboard unavailable: {message}")
            return None

        result = dict(report)
        self._set_value_dashboard_from_report(result, update_status=update_status)
        return result

    def _selected_release_id_or_raise(self) -> int:
        if self._selected_release_id is None:
            raise ValueError("Select a release first.")
        return self._selected_release_id

    def _friendly_error_message(self, exc: Exception) -> str:
        if isinstance(
            exc,
            (
                DiscogsDependencyError,
                DiscogsAuthError,
                DiscogsApiError,
                PlayerDependencyError,
                PlayerAuthError,
                PlayerApiError,
                PlayerPlaybackError,
                MatchingDependencyError,
                NoSpotifyDevicesError,
                MissingLastSpinError,
                MissingDiscogsTokenError,
                ValueError,
            ),
        ):
            return str(exc)
        return f"{type(exc).__name__}: {exc}"

    def _spotify_playback_available(self) -> bool:
        return bool(
            self._spotify_capability.addon_available
            and self._spotify_capability.configured
        )

    def _open_spotify_url(self, url: str) -> bool:
        target = str(url or "").strip()
        if not target:
            return False
        try:
            import webbrowser

            webbrowser.open(target)
            return True
        except Exception:
            return False

    def _start_async_action(
        self,
        *,
        action_key: str,
        busy_message: str,
        runner: Callable[[], dict[str, object]],
        on_success: Callable[[dict[str, object]], None],
        on_error: Callable[[str], None],
        on_started: Callable[[], None] | None = None,
        on_finished: Callable[[], None] | None = None,
        duplicate_message: str | None = None,
    ) -> bool:
        if action_key in self._inflight_actions:
            self._set_status(duplicate_message or "Action already in progress.")
            return False

        self._inflight_actions.add(action_key)
        if on_started is not None:
            on_started()
        self._set_status(busy_message)
        try:
            future = self._actions_executor.submit(runner)
        except RuntimeError as exc:
            self._inflight_actions.discard(action_key)
            if on_finished is not None:
                on_finished()
            on_error(self._friendly_error_message(exc))
            return False
        def _on_complete(completed: Future[dict[str, object]]) -> None:
            GLib.idle_add(
                self._complete_async_action,
                action_key,
                completed,
                on_success,
                on_error,
                on_finished,
            )

        future.add_done_callback(_on_complete)
        return True

    def _complete_async_action(
        self,
        action_key: str,
        future: Future[dict[str, object]],
        on_success: Callable[[dict[str, object]], None],
        on_error: Callable[[str], None],
        on_finished: Callable[[], None] | None,
    ) -> bool:
        self._inflight_actions.discard(action_key)
        try:
            payload = dict(future.result())
        except Exception as exc:
            on_error(self._friendly_error_message(exc))
        else:
            try:
                on_success(payload)
            except Exception as exc:
                on_error(self._friendly_error_message(exc))
        finally:
            if on_finished is not None:
                on_finished()
        return False

    def _set_album_actions_busy(self, busy: bool) -> None:
        self._album_detail.set_actions_enabled(
            (not busy) and self._selected_release_id is not None
        )
        self._album_detail.set_global_spotify_actions_enabled(not busy)

    def _set_device_actions_busy(self, busy: bool) -> None:
        self._device_picker.set_actions_enabled(not busy)

    def _handle_album_action_error(self, message: str) -> None:
        self._album_detail.set_error(message)
        self._set_status(message)

    def _handle_device_action_error(self, message: str) -> None:
        self._device_picker.set_error(message)
        self._set_status(message)

    def _handle_spin_error(self, message: str) -> None:
        self._carousel.stop_center_spin_animation()
        self._pending_spin_result = None
        self._spin_wheel.set_error(message)
        self._set_status(message)

    def _run_release_load_operation(
        self,
        *,
        q: str | None,
        year: str | None,
        genres: list[str] | None,
        styles: list[str] | None,
        unmatched: bool,
        sort_mode: str,
        limit: int | None,
    ) -> dict[str, object]:
        effective_limit = _normalize_release_limit(
            limit if limit is not None else self._limit
        )
        normalized_genres = list(genres or [])
        normalized_styles = list(styles or [])
        # Hotspot 1: DB query + cover prefetch
        _t0 = time.perf_counter()
        items_raw = run_browse_release_grid(
            limit=effective_limit,
            q=q,
            year=year,
            genres=normalized_genres,
            styles=normalized_styles,
            unmatched=unmatched,
            preload_covers=self._preload_covers,
        )
        _t_query = time.perf_counter() - _t0
        # Hotspot 2: in-memory sort
        _t1 = time.perf_counter()
        items = sort_release_items(items_raw, sort_mode=sort_mode)
        _t_sort = time.perf_counter() - _t1
        cover_count = sum(1 for item in items if item.get("cover_path"))

        value_dashboard_report: dict[str, object] | None = None
        value_dashboard_error: str | None = None
        try:
            value_dashboard_report = dict(
                run_market_value_dashboard(
                    top_limit=_VALUE_DASHBOARD_TOP_LIMIT,
                    bottom_limit=_VALUE_DASHBOARD_BOTTOM_LIMIT,
                    trend_limit=_VALUE_DASHBOARD_TREND_LIMIT,
                )
            )
        except Exception as exc:
            value_dashboard_error = self._friendly_error_message(exc)

        return {
            "ok": True,
            "items": items,
            "item_count": len(items),
            "cover_cached_count": cover_count,
            "query": q,
            "year": year,
            "genres": normalized_genres,
            "styles": normalized_styles,
            "unmatched": unmatched,
            "sort": sort_mode,
            "limit": effective_limit,
            "value_dashboard_report": value_dashboard_report,
            "value_dashboard_error": value_dashboard_error,
            "_timing_query_s": _t_query,
            "_timing_sort_s": _t_sort,
        }

    def _apply_release_load_result(
        self,
        payload: dict[str, object],
        *,
        preferred_release_id: int | None,
    ) -> dict[str, object]:
        items_raw = payload.get("items")
        items = (
            [dict(item) for item in items_raw if isinstance(item, dict)]
            if isinstance(items_raw, list)
            else []
        )
        self._visible_release_ids = [
            int(item["discogs_release_id"])
            for item in items
            if isinstance(item.get("discogs_release_id"), int)
        ]
        self._visible_release_id_to_index = self._build_id_index_map(
            self._visible_release_ids
        )

        value_dashboard_error = str(payload.get("value_dashboard_error") or "").strip()
        if value_dashboard_error:
            self._value_dashboard.set_error(value_dashboard_error)
        else:
            value_dashboard_raw = payload.get("value_dashboard_report")
            value_dashboard = (
                dict(value_dashboard_raw)
                if isinstance(value_dashboard_raw, dict)
                else {}
            )
            if value_dashboard:
                self._set_value_dashboard_from_report(
                    value_dashboard, update_status=False
                )

        # Hotspot 3: widget population (main thread)
        _t2 = time.perf_counter()
        self._syncing_selection = True
        try:
            self._text_menu.set_items(items)
            self._carousel.set_items(items)
            self._browse_gallery.set_items(items)
        finally:
            self._syncing_selection = False
        _t_widgets = time.perf_counter() - _t2

        if _TIMING_ENABLED:
            _rq = payload.get("_timing_query_s")
            _rs = payload.get("_timing_sort_s")
            _t_query = float(_rq) if isinstance(_rq, (int, float)) else 0.0
            _t_sort = float(_rs) if isinstance(_rs, (int, float)) else 0.0
            print(
                f"[timing] browse-load: n={len(items)}"
                f"  query={_t_query * 1000:.1f}ms"
                f"  sort={_t_sort * 1000:.1f}ms"
                f"  widgets={_t_widgets * 1000:.1f}ms",
                file=sys.stderr,
                flush=True,
            )

        restored_selection = False
        if isinstance(preferred_release_id, int):
            restored_selection = self._focus_release_id(
                preferred_release_id,
                allow_expand_limit=False,
            )

        if not restored_selection and items:
            if self._active_browse_mode() == "gallery":
                self._handle_release_selected(None)
            else:
                first_release_id = items[0].get("discogs_release_id")
                if isinstance(first_release_id, int):
                    self._focus_release_id(first_release_id, allow_expand_limit=False)
                else:
                    self._handle_release_selected(items[0])
        elif not items:
            self._visible_release_ids = []
            self._visible_release_id_to_index = {}
            self._handle_release_selected(None)

        cover_count = _to_int(payload.get("cover_cached_count"))
        if not items:
            self._album_detail.set_release(None)
            token_missing = not bool(get_discogs_token())
            self._update_setup_state(token_missing=token_missing)
            if token_missing:
                self._browse_empty_box.set_visible(False)
                self._set_status(
                    "Connect your Discogs account to get started \u2014 use the banner above."
                )
            else:
                self._browse_empty_box.set_visible(True)
                last_sync = get_setting("last_sync_time")
                if last_sync is None:
                    status_msg = (
                        "No releases synced yet. Click \"Sync Collection\" to import"
                        " your Discogs collection for the first time."
                    )
                    self._browse_empty_label.set_text(
                        "Sync your collection to get started."
                    )
                else:
                    status_msg = "No releases match the current filters."
                    self._browse_empty_label.set_text(
                        "No releases match the current filters."
                    )
                self._set_status(status_msg)
        else:
            self._browse_empty_box.set_visible(False)
            self._update_setup_state(token_missing=False)
            last_sync = get_setting("last_sync_time")
            self._set_status(
                f"Loaded {len(items)} releases"
                f" ({cover_count} covers cached)"
                f" · Last synced {_format_sync_date(last_sync)}"
            )

        # Emit startup timing when the first load completes (item 6).
        if _TIMING_ENABLED:
            _t0 = getattr(self, "_startup_load_t0", None)
            if isinstance(_t0, float):
                _t_startup = time.perf_counter() - _t0
                print(
                    f"[timing] startup-load: first-load-total={_t_startup * 1000:.1f}ms"
                    f" n={len(items)}",
                    file=sys.stderr,
                    flush=True,
                )
                del self._startup_load_t0  # type: ignore[attr-defined]

        # Sidebar/detail content can change natural width after load; reapply split.
        GLib.idle_add(self._apply_split_layout_from_current_size)
        GLib.timeout_add(120, self._apply_split_layout_from_current_size)

        return {
            "ok": True,
            "item_count": len(items),
            "cover_cached_count": cover_count,
            "query": payload.get("query"),
            "year": payload.get("year"),
            "genres": payload.get("genres")
            if isinstance(payload.get("genres"), list)
            else [],
            "styles": payload.get("styles")
            if isinstance(payload.get("styles"), list)
            else [],
            "unmatched": bool(payload.get("unmatched")),
            "sort": str(payload.get("sort") or "artist_title"),
            "limit": _normalize_release_limit(payload.get("limit")),
        }

    def _handle_release_load_error(self, message: str) -> None:
        self._set_status(message)

    def _run_wantlist_load_operation(
        self,
        *,
        q: str | None,
        year: str | None,
        genres: list[str] | None,
        styles: list[str] | None,
        sort_mode: str,
        limit: int | None,
    ) -> dict[str, object]:
        effective_limit = _normalize_release_limit(
            limit if limit is not None else self._limit
        )
        normalized_genres = list(genres or [])
        normalized_styles = list(styles or [])
        # Hotspot 1: DB query + cover prefetch
        _t0 = time.perf_counter()
        items_raw = run_browse_wantlist_grid(
            limit=effective_limit,
            q=q,
            year=year,
            genres=normalized_genres,
            styles=normalized_styles,
            preload_covers=self._preload_covers,
        )
        _t_query = time.perf_counter() - _t0
        # Hotspot 2: in-memory sort
        _t1 = time.perf_counter()
        items = sort_release_items(items_raw, sort_mode=sort_mode)
        _t_sort = time.perf_counter() - _t1
        cover_count = sum(1 for item in items if item.get("cover_path"))
        return {
            "ok": True,
            "items": items,
            "item_count": len(items),
            "cover_cached_count": cover_count,
            "query": q,
            "year": year,
            "genres": normalized_genres,
            "styles": normalized_styles,
            "sort": sort_mode,
            "limit": effective_limit,
            "_timing_query_s": _t_query,
            "_timing_sort_s": _t_sort,
        }

    def _apply_wantlist_load_result(
        self,
        payload: dict[str, object],
        *,
        preferred_release_id: int | None,
    ) -> dict[str, object]:
        items_raw = payload.get("items")
        items = (
            [dict(item) for item in items_raw if isinstance(item, dict)]
            if isinstance(items_raw, list)
            else []
        )
        self._visible_wantlist_ids = [
            int(item["discogs_release_id"])
            for item in items
            if isinstance(item.get("discogs_release_id"), int)
        ]
        self._visible_wantlist_id_to_index = self._build_id_index_map(
            self._visible_wantlist_ids
        )

        # Hotspot 3: widget population (main thread)
        _t2 = time.perf_counter()
        self._wantlist_syncing_selection = True
        try:
            self._wantlist_text_menu.set_items(items)
            self._wantlist_carousel.set_items(items)
            self._wantlist_gallery.set_items(items)
        finally:
            self._wantlist_syncing_selection = False
        _t_widgets = time.perf_counter() - _t2

        if _TIMING_ENABLED:
            _rq = payload.get("_timing_query_s")
            _rs = payload.get("_timing_sort_s")
            _t_query = float(_rq) if isinstance(_rq, (int, float)) else 0.0
            _t_sort = float(_rs) if isinstance(_rs, (int, float)) else 0.0
            print(
                f"[timing] wantlist-load: n={len(items)}"
                f"  query={_t_query * 1000:.1f}ms"
                f"  sort={_t_sort * 1000:.1f}ms"
                f"  widgets={_t_widgets * 1000:.1f}ms",
                file=sys.stderr,
                flush=True,
            )

        restored_selection = False
        if isinstance(preferred_release_id, int):
            restored_selection = self._focus_wantlist_id(
                preferred_release_id,
                allow_expand_limit=False,
            )

        if not restored_selection and items:
            if self._active_wantlist_mode() == "gallery":
                self._handle_wantlist_selected(None)
            else:
                first_release_id = items[0].get("discogs_release_id")
                if isinstance(first_release_id, int):
                    self._focus_wantlist_id(first_release_id, allow_expand_limit=False)
                else:
                    self._handle_wantlist_selected(items[0])
        elif not items:
            self._visible_wantlist_ids = []
            self._visible_wantlist_id_to_index = {}
            self._handle_wantlist_selected(None)

        cover_count = _to_int(payload.get("cover_cached_count"))
        if not items:
            self._wantlist_detail.set_entry(None)
            self._wantlist_empty_box.set_visible(True)
            token_missing = not bool(get_discogs_token())
            last_sync = get_setting("last_wantlist_sync_time")
            if last_sync is None:
                last_sync = get_setting("last_sync_time")
            if token_missing:
                wl_status = (
                    "Connect your Discogs account to get started \u2014 use the banner above."
                )
                self._wantlist_empty_label.set_text(
                    "Connect Discogs to browse your wantlist."
                )
            elif last_sync is None:
                wl_status = (
                    "No wantlist synced yet. Click \"Sync Wantlist\" to import"
                    " your Discogs wantlist for the first time."
                )
                self._wantlist_empty_label.set_text(
                    "Sync your wantlist to get started."
                )
            else:
                wl_status = "No wantlist items match the current filters."
                self._wantlist_empty_label.set_text(
                    "No wantlist items match the current filters."
                )
            self._set_status(wl_status)
        else:
            self._wantlist_empty_box.set_visible(False)
            wl_last_sync = get_setting("last_wantlist_sync_time")
            self._set_status(
                f"Loaded {len(items)} wantlist items"
                f" ({cover_count} covers cached)"
                f" · Last synced {_format_sync_date(wl_last_sync)}"
            )

        # Sidebar/detail content can change natural width after load; reapply split.
        GLib.idle_add(self._apply_split_layout_from_current_size)
        GLib.timeout_add(120, self._apply_split_layout_from_current_size)

        return {
            "ok": True,
            "item_count": len(items),
            "cover_cached_count": cover_count,
            "query": payload.get("query"),
            "year": payload.get("year"),
            "genres": payload.get("genres")
            if isinstance(payload.get("genres"), list)
            else [],
            "styles": payload.get("styles")
            if isinstance(payload.get("styles"), list)
            else [],
            "sort": str(payload.get("sort") or "artist_title"),
            "limit": _normalize_release_limit(payload.get("limit")),
        }

    def _handle_wantlist_load_error(self, message: str) -> None:
        self._wantlist_detail.set_error(message)
        self._set_status(message)

    def _focus_wantlist_id(
        self, discogs_release_id: int, *, allow_expand_limit: bool = True
    ) -> bool:
        selected = False
        if self._wantlist_text_menu.select_release(discogs_release_id):
            selected = True
        if self._wantlist_carousel.select_release(discogs_release_id):
            selected = True
        if (
            self._active_wantlist_mode() == "gallery"
            and self._wantlist_gallery.select_release(discogs_release_id)
        ):
            selected = True
        if selected:
            return True

        if not allow_expand_limit:
            return False

        filters = self._current_wantlist_filters()
        current_limit = _normalize_release_limit(filters.get("limit"))
        expanded_limit = None if current_limit is None else max(current_limit, 250)
        self.load_wantlist_with_filters(
            q=filters.get("q"),  # type: ignore[arg-type]
            year=filters.get("year"),  # type: ignore[arg-type]
            genres=filters.get("genres"),  # type: ignore[arg-type]
            styles=filters.get("styles"),  # type: ignore[arg-type]
            sort_mode=str(filters.get("sort") or "artist_title"),
            limit=expanded_limit,
            background=False,
        )
        selected = False
        if self._wantlist_text_menu.select_release(discogs_release_id):
            selected = True
        if self._wantlist_carousel.select_release(discogs_release_id):
            selected = True
        if (
            self._active_wantlist_mode() == "gallery"
            and self._wantlist_gallery.select_release(discogs_release_id)
        ):
            selected = True
        return selected

    def _should_reflow_gallery_split(
        self,
        *,
        mode: str,
        had_selection: bool,
        has_selection: bool,
    ) -> bool:
        return str(mode) == "gallery" and bool(had_selection) != bool(has_selection)

    def _handle_wantlist_selected(self, item: dict[str, object] | None) -> None:
        had_selection = isinstance(self._selected_wantlist_id, int)
        mode = self._active_wantlist_mode()
        if isinstance(item, dict) and isinstance(item.get("discogs_release_id"), int):
            detail_item = self._wantlist_with_cached_tracklist(item)
            self._selected_wantlist = dict(detail_item)
            self._selected_wantlist_id = _to_int(item.get("discogs_release_id"))
            self._wantlist_detail.set_entry(detail_item)
            self._wantlist_spin_wheel.set_context_release(detail_item)
            artist = str(item.get("artist") or "Unknown Artist")
            title = str(item.get("title") or "Unknown Title")
            self._set_status(
                f"Selected wantlist item {self._selected_wantlist_id}: {artist} - {title}"
            )
            self._sync_wantlist_selection(self._selected_wantlist_id)
            if (
                self._active_main_view() == "wantlist"
                and self._should_reflow_gallery_split(
                    mode=mode,
                    had_selection=had_selection,
                    has_selection=True,
                )
            ):
                GLib.idle_add(self._apply_split_layout_from_current_size)
            return

        self._selected_wantlist = None
        self._selected_wantlist_id = None
        self._wantlist_gallery.clear_selection(emit=False)
        self._wantlist_detail.set_entry(None)
        self._wantlist_spin_wheel.set_context_release(None)
        if self._active_wantlist_mode() == "gallery":
            self._set_status("Wantlist gallery selection cleared.")
        else:
            self._set_status("No wantlist item selected.")
        if (
            self._active_main_view() == "wantlist"
            and self._should_reflow_gallery_split(
                mode=mode,
                had_selection=had_selection,
                has_selection=False,
            )
        ):
            GLib.idle_add(self._apply_split_layout_from_current_size)

    def _focus_release_id(
        self, discogs_release_id: int, *, allow_expand_limit: bool = True
    ) -> bool:
        selected = False
        if self._text_menu.select_release(discogs_release_id):
            selected = True
        if self._carousel.select_release(discogs_release_id):
            selected = True
        if (
            self._active_browse_mode() == "gallery"
            and self._browse_gallery.select_release(discogs_release_id)
        ):
            selected = True
        if selected:
            return True

        if not allow_expand_limit:
            return False

        filters = self._current_filters()
        current_limit = _normalize_release_limit(filters.get("limit"))
        expanded_limit = None if current_limit is None else max(current_limit, 250)
        self.load_releases_with_filters(
            q=filters.get("q"),  # type: ignore[arg-type]
            year=filters.get("year"),  # type: ignore[arg-type]
            genres=filters.get("genres"),  # type: ignore[arg-type]
            styles=filters.get("styles"),  # type: ignore[arg-type]
            unmatched=bool(filters.get("unmatched")),
            sort_mode=str(filters.get("sort") or "artist_title"),
            limit=expanded_limit,
            background=False,
        )
        selected = False
        if self._text_menu.select_release(discogs_release_id):
            selected = True
        if self._carousel.select_release(discogs_release_id):
            selected = True
        if (
            self._active_browse_mode() == "gallery"
            and self._browse_gallery.select_release(discogs_release_id)
        ):
            selected = True
        return selected

    def _handle_release_selected(self, item: dict[str, object] | None) -> None:
        had_selection = isinstance(self._selected_release_id, int)
        mode = self._active_browse_mode()
        if isinstance(item, dict) and isinstance(item.get("discogs_release_id"), int):
            detail_item = self._release_with_cached_tracklist(item)
            self._selected_release = dict(detail_item)
            self._selected_release_id = _to_int(item.get("discogs_release_id"))
            self._album_detail.set_release(detail_item)
            self._spin_wheel.set_context_release(item)
            artist = str(item.get("artist") or "Unknown Artist")
            title = str(item.get("title") or "Unknown Title")
            self._set_status(
                f"Selected release {self._selected_release_id}: {artist} - {title}"
            )
            self._sync_release_selection(self._selected_release_id)
            if (
                self._active_main_view() == "browse"
                and self._should_reflow_gallery_split(
                    mode=mode,
                    had_selection=had_selection,
                    has_selection=True,
                )
            ):
                GLib.idle_add(self._apply_split_layout_from_current_size)
            return

        self._selected_release = None
        self._selected_release_id = None
        self._browse_gallery.clear_selection(emit=False)
        self._album_detail.set_release(None)
        self._spin_wheel.set_context_release(None)
        if self._active_browse_mode() == "gallery":
            self._set_status("Browse gallery selection cleared.")
        else:
            self._set_status("No release selected.")
        if (
            self._active_main_view() == "browse"
            and self._should_reflow_gallery_split(
                mode=mode,
                had_selection=had_selection,
                has_selection=False,
            )
        ):
            GLib.idle_add(self._apply_split_layout_from_current_size)

    def _handle_auto_match_clicked(self) -> None:
        try:
            release_id = self._selected_release_id_or_raise()
        except Exception as exc:
            self._handle_album_action_error(self._friendly_error_message(exc))
            return

        self._start_async_action(
            action_key="album-action",
            busy_message=f"Auto-matching release {release_id}...",
            duplicate_message="Album action already in progress.",
            runner=lambda: run_match_action(release_id),
            on_started=lambda: self._set_album_actions_busy(True),
            on_finished=lambda: self._set_album_actions_busy(False),
            on_success=self._apply_auto_match_result,
            on_error=self._handle_album_action_error,
        )

    def _apply_auto_match_result(self, payload: dict[str, object]) -> None:
        self._album_detail.set_match_result(payload)
        self._set_status(str(payload.get("status_message") or "Auto-match completed."))
        if self._selected_release is not None:
            self._selected_release["spotify_album_id"] = payload.get("spotify_album_id")
        if isinstance(self._selected_release_id, int):
            self._browse_gallery.set_release_spotify_album_id(
                self._selected_release_id, payload.get("spotify_album_id")
            )

    def _handle_match_audit_clicked(self) -> None:
        if not self._spotify_playback_available():
            self._set_status(
                "Connect Spotify before running match audit in the desktop app."
            )
            return

        self._start_async_action(
            action_key="match-audit",
            busy_message="Auditing unmatched Spotify mappings...",
            duplicate_message="Match audit already in progress.",
            runner=lambda: run_match_audit_action(apply_safe_matches=False, resume=True),
            on_started=lambda: self._set_album_actions_busy(True),
            on_finished=lambda: self._set_album_actions_busy(False),
            on_success=self._apply_match_audit_result,
            on_error=self._handle_album_action_error,
        )

    def _handle_apply_safe_matches_clicked(self) -> None:
        if not self._spotify_playback_available():
            self._set_status(
                "Connect Spotify before applying safe matches in the desktop app."
            )
            return

        self._start_async_action(
            action_key="match-audit",
            busy_message="Applying safe Spotify matches and updating audit report...",
            duplicate_message="Match audit already in progress.",
            runner=lambda: run_match_audit_action(apply_safe_matches=True, resume=True),
            on_started=lambda: self._set_album_actions_busy(True),
            on_finished=lambda: self._set_album_actions_busy(False),
            on_success=self._apply_match_audit_result,
            on_error=self._handle_album_action_error,
        )

    def _handle_apply_review_queue_clicked(self) -> None:
        if not self._spotify_playback_available():
            self._set_status(
                "Connect Spotify before applying review-candidate matches."
            )
            return

        self._start_async_action(
            action_key="match-review",
            busy_message="Applying review-candidate Spotify mappings...",
            duplicate_message="Match review action already in progress.",
            runner=lambda: run_match_review_apply_action(apply_all=True),
            on_started=lambda: self._set_album_actions_busy(True),
            on_finished=lambda: self._set_album_actions_busy(False),
            on_success=self._apply_match_review_result,
            on_error=self._handle_album_action_error,
        )

    def _handle_reject_review_queue_clicked(self) -> None:
        if not self._spotify_playback_available():
            self._set_status(
                "Connect Spotify before rejecting review-candidate matches."
            )
            return

        self._start_async_action(
            action_key="match-review",
            busy_message="Rejecting review-candidate Spotify mappings...",
            duplicate_message="Match review action already in progress.",
            runner=lambda: run_match_review_reject_action(apply_all=True),
            on_started=lambda: self._set_album_actions_busy(True),
            on_finished=lambda: self._set_album_actions_busy(False),
            on_success=self._apply_match_review_result,
            on_error=self._handle_album_action_error,
        )

    def _handle_retry_audit_errors_clicked(self) -> None:
        if not self._spotify_playback_available():
            self._set_status(
                "Connect Spotify before retrying audit error entries."
            )
            return

        self._start_async_action(
            action_key="match-audit",
            busy_message="Retrying previously errored audit entries...",
            duplicate_message="Match audit already in progress.",
            runner=lambda: run_match_retry_errors_action(),
            on_started=lambda: self._set_album_actions_busy(True),
            on_finished=lambda: self._set_album_actions_busy(False),
            on_success=self._apply_match_audit_result,
            on_error=self._handle_album_action_error,
        )

    def _apply_match_audit_result(self, payload: dict[str, object]) -> None:
        self._album_detail.set_match_audit_result(payload)
        self._set_status(str(payload.get("status_message") or "Match audit completed."))
        if _to_int(payload.get("run_auto_applied_count")) > 0:
            self.refresh()

    def _apply_match_review_result(self, payload: dict[str, object]) -> None:
        self._album_detail.set_match_review_result(payload)
        self._set_status(
            str(payload.get("status_message") or "Match review action completed.")
        )
        action = str(payload.get("action") or "")
        if action == "match_review_apply" and _to_int(payload.get("updated_count")) > 0:
            self.refresh()

    def _handle_override_clicked(self) -> None:
        try:
            release_id = self._selected_release_id_or_raise()
            spotify_album_id = self._album_detail.get_override_album_id()
        except Exception as exc:
            self._handle_album_action_error(self._friendly_error_message(exc))
            return

        self._start_async_action(
            action_key="album-action",
            busy_message=f"Saving override for release {release_id}...",
            duplicate_message="Album action already in progress.",
            runner=lambda: run_override_action(release_id, spotify_album_id),
            on_started=lambda: self._set_album_actions_busy(True),
            on_finished=lambda: self._set_album_actions_busy(False),
            on_success=self._apply_override_result,
            on_error=self._handle_album_action_error,
        )

    def _apply_override_result(self, payload: dict[str, object]) -> None:
        self._album_detail.set_override_result(payload)
        self._set_status(str(payload.get("status_message") or "Override saved."))
        if self._selected_release is not None:
            self._selected_release["spotify_album_id"] = payload.get("spotify_album_id")
        if isinstance(self._selected_release_id, int):
            self._browse_gallery.set_release_spotify_album_id(
                self._selected_release_id, payload.get("spotify_album_id")
            )

    def _handle_play_clicked(self) -> None:
        try:
            release_id = self._selected_release_id_or_raise()
        except Exception as exc:
            self._handle_album_action_error(self._friendly_error_message(exc))
            return

        self._start_async_action(
            action_key="album-play-action",
            busy_message=(
                f"Starting playback for release {release_id}..."
                if self._spotify_playback_available()
                else f"Preparing Spotify URL for release {release_id}..."
            ),
            duplicate_message="Play action already in progress.",
            runner=lambda: run_play_action(release_id),
            on_started=lambda: self._set_album_actions_busy(True),
            on_finished=lambda: self._set_album_actions_busy(False),
            on_success=self._apply_play_result,
            on_error=self._handle_album_action_error,
        )

    def _apply_play_result(self, payload: dict[str, object]) -> None:
        if self._selected_release is not None:
            album_id = payload.get("spotify_album_id")
            if album_id:
                self._selected_release["spotify_album_id"] = album_id
                if isinstance(self._selected_release_id, int):
                    self._browse_gallery.set_release_spotify_album_id(
                        self._selected_release_id, album_id
                    )

        if not self._spotify_playback_available():
            raw = payload.get("raw")
            if isinstance(raw, dict):
                fallback_url = str(raw.get("fallback_open_url") or "").strip()
                if fallback_url and self._open_spotify_url(fallback_url):
                    opened_message = f"Opened in Spotify: {fallback_url}"
                    self._album_detail.set_play_result({"status_message": opened_message})
                    self._set_status(opened_message)
                    return

        self._album_detail.set_play_result(payload)
        self._set_status(str(payload.get("status_message") or "Play action completed."))

    def _handle_tracklist_refresh_clicked(self) -> None:
        try:
            release_id = self._selected_release_id_or_raise()
        except Exception as exc:
            self._handle_album_action_error(self._friendly_error_message(exc))
            return

        self._start_async_action(
            action_key="album-action",
            busy_message=f"Refreshing tracklist for release {release_id}...",
            duplicate_message="Album action already in progress.",
            # runner=lambda rid=release_id: run_release_tracklist_show(rid, refresh=True)
            runner=lambda: run_release_tracklist_show(release_id, refresh=True),
            on_started=lambda: self._set_album_actions_busy(True),
            on_finished=lambda: self._set_album_actions_busy(False),
            on_success=self._apply_tracklist_refresh_result,
            on_error=self._handle_album_action_error,
        )

    def _apply_tracklist_refresh_result(self, payload: dict[str, object]) -> None:
        release_id = payload.get("discogs_release_id")
        selected = (
            dict(self._selected_release)
            if isinstance(self._selected_release, dict)
            else {}
        )
        if isinstance(release_id, int):
            selected["discogs_release_id"] = release_id
            self._selected_release_id = release_id
            self._tracklist_cache_invalidate(
                self._release_tracklist_cache, release_id=release_id
            )
        detail_item = self._release_with_cached_tracklist(selected)
        self._selected_release = dict(detail_item)
        self._album_detail.set_release(detail_item)

        release_id_text = str(release_id) if isinstance(release_id, int) else "n/a"
        track_count = _to_int(detail_item.get("track_count"))
        audio_count = _to_int(detail_item.get("audio_track_count"))
        self._set_status(
            f"Tracklist refreshed for release {release_id_text} ({audio_count}/{track_count} audio tracks)."
        )

    def _selected_wantlist_id_or_raise(self) -> int:
        if self._selected_wantlist_id is None:
            raise ValueError("Select a wantlist item first.")
        return self._selected_wantlist_id

    def _set_wantlist_actions_busy(self, busy: bool) -> None:
        self._wantlist_detail.set_actions_enabled(
            (not busy) and self._selected_wantlist_id is not None
        )

    def _handle_wantlist_action_error(self, message: str) -> None:
        self._wantlist_detail.set_error(message)
        self._set_status(message)

    def _handle_wantlist_auto_match_clicked(self) -> None:
        try:
            release_id = self._selected_wantlist_id_or_raise()
        except Exception as exc:
            self._handle_wantlist_action_error(self._friendly_error_message(exc))
            return

        self._start_async_action(
            action_key="wantlist-action",
            busy_message=f"Auto-matching wantlist release {release_id}...",
            duplicate_message="Wantlist action already in progress.",
            runner=lambda: run_match_action(release_id),
            on_started=lambda: self._set_wantlist_actions_busy(True),
            on_finished=lambda: self._set_wantlist_actions_busy(False),
            on_success=self._apply_wantlist_auto_match_result,
            on_error=self._handle_wantlist_action_error,
        )

    def _apply_wantlist_auto_match_result(self, payload: dict[str, object]) -> None:
        self._wantlist_detail.set_match_result(payload)
        self._set_status(
            str(payload.get("status_message") or "Wantlist auto-match completed.")
        )
        if self._selected_wantlist is not None:
            self._selected_wantlist["spotify_album_id"] = payload.get("spotify_album_id")
        if isinstance(self._selected_wantlist_id, int):
            self._wantlist_gallery.set_release_spotify_album_id(
                self._selected_wantlist_id, payload.get("spotify_album_id")
            )

    def _handle_wantlist_override_clicked(self) -> None:
        try:
            release_id = self._selected_wantlist_id_or_raise()
            spotify_album_id = self._wantlist_detail.get_override_album_id()
        except Exception as exc:
            self._handle_wantlist_action_error(self._friendly_error_message(exc))
            return

        self._start_async_action(
            action_key="wantlist-action",
            busy_message=f"Saving wantlist override for release {release_id}...",
            duplicate_message="Wantlist action already in progress.",
            runner=lambda: run_override_action(release_id, spotify_album_id),
            on_started=lambda: self._set_wantlist_actions_busy(True),
            on_finished=lambda: self._set_wantlist_actions_busy(False),
            on_success=self._apply_wantlist_override_result,
            on_error=self._handle_wantlist_action_error,
        )

    def _apply_wantlist_override_result(self, payload: dict[str, object]) -> None:
        self._wantlist_detail.set_override_result(payload)
        self._set_status(str(payload.get("status_message") or "Wantlist override saved."))
        if self._selected_wantlist is not None:
            self._selected_wantlist["spotify_album_id"] = payload.get("spotify_album_id")
        if isinstance(self._selected_wantlist_id, int):
            self._wantlist_gallery.set_release_spotify_album_id(
                self._selected_wantlist_id, payload.get("spotify_album_id")
            )

    def _handle_wantlist_play_clicked(self) -> None:
        try:
            release_id = self._selected_wantlist_id_or_raise()
        except Exception as exc:
            self._handle_wantlist_action_error(self._friendly_error_message(exc))
            return

        self._start_async_action(
            action_key="wantlist-play-action",
            busy_message=(
                f"Starting playback for wantlist release {release_id}..."
                if self._spotify_playback_available()
                else f"Preparing Spotify URL for wantlist release {release_id}..."
            ),
            duplicate_message="Wantlist play action already in progress.",
            runner=lambda: run_play_action(release_id),
            on_started=lambda: self._set_wantlist_actions_busy(True),
            on_finished=lambda: self._set_wantlist_actions_busy(False),
            on_success=self._apply_wantlist_play_result,
            on_error=self._handle_wantlist_action_error,
        )

    def _apply_wantlist_play_result(self, payload: dict[str, object]) -> None:
        if self._selected_wantlist is not None:
            album_id = payload.get("spotify_album_id")
            if album_id:
                self._selected_wantlist["spotify_album_id"] = album_id
                if isinstance(self._selected_wantlist_id, int):
                    self._wantlist_gallery.set_release_spotify_album_id(
                        self._selected_wantlist_id, album_id
                    )

        if not self._spotify_playback_available():
            raw = payload.get("raw")
            if isinstance(raw, dict):
                fallback_url = str(raw.get("fallback_open_url") or "").strip()
                if fallback_url and self._open_spotify_url(fallback_url):
                    opened_message = f"Opened in Spotify: {fallback_url}"
                    self._wantlist_detail.set_play_result(
                        {"status_message": opened_message}
                    )
                    self._set_status(opened_message)
                    return

        self._wantlist_detail.set_play_result(payload)
        self._set_status(
            str(payload.get("status_message") or "Wantlist play action completed.")
        )

    def _handle_wantlist_tracklist_refresh_clicked(self) -> None:
        try:
            release_id = self._selected_wantlist_id_or_raise()
        except Exception as exc:
            message = self._friendly_error_message(exc)
            self._wantlist_detail.set_error(message)
            self._set_status(message)
            return

        self._start_async_action(
            action_key="wantlist-action",
            busy_message=f"Refreshing tracklist for wantlist release {release_id}...",
            duplicate_message="Wantlist action already in progress.",
            runner=lambda: run_wantlist_tracklist_show(release_id, refresh=True),
            on_started=lambda: self._set_wantlist_actions_busy(True),
            on_finished=lambda: self._set_wantlist_actions_busy(False),
            on_success=self._apply_wantlist_tracklist_refresh_result,
            on_error=self._handle_wantlist_action_error,
        )

    def _apply_wantlist_tracklist_refresh_result(
        self, payload: dict[str, object]
    ) -> None:
        release_id = payload.get("discogs_release_id")
        selected = (
            dict(self._selected_wantlist)
            if isinstance(self._selected_wantlist, dict)
            else {}
        )
        if isinstance(release_id, int):
            selected["discogs_release_id"] = release_id
            self._selected_wantlist_id = release_id
            self._tracklist_cache_invalidate(
                self._wantlist_tracklist_cache, release_id=release_id
            )

        detail_item = dict(selected)
        tracklist_payload = self._normalize_tracklist_payload(
            {
                "tracks": payload.get("tracks"),
                "track_count": payload.get("track_count"),
                "audio_track_count": payload.get("audio_track_count"),
                "tracklist_last_refreshed_at": payload.get(
                    "tracklist_last_refreshed_at"
                ),
                "has_cached_tracklist": payload.get("has_cached_tracklist"),
                "has_tracklist": payload.get("has_tracklist"),
                "has_audio_tracks": payload.get("has_audio_tracks"),
            }
        )
        detail_item.update(tracklist_payload)
        if isinstance(release_id, int):
            self._tracklist_cache_put(
                self._wantlist_tracklist_cache,
                release_id=release_id,
                payload=tracklist_payload,
            )
        self._selected_wantlist = dict(detail_item)
        self._wantlist_detail.set_entry(detail_item)

        release_id_text = str(release_id) if isinstance(release_id, int) else "n/a"
        track_count = _to_int(detail_item.get("track_count"))
        audio_count = _to_int(detail_item.get("audio_track_count"))
        self._set_status(
            f"Tracklist refreshed for wantlist release {release_id_text} ({audio_count}/{track_count} audio tracks)."
        )

    def _handle_wantlist_pricing_refresh_clicked(self) -> None:
        try:
            release_id = self._selected_wantlist_id_or_raise()
        except Exception as exc:
            message = self._friendly_error_message(exc)
            self._wantlist_detail.set_error(message)
            self._set_status(message)
            return

        self._start_async_action(
            action_key="wantlist-action",
            busy_message=f"Refreshing pricing for wantlist release {release_id}...",
            duplicate_message="Wantlist action already in progress.",
            runner=lambda: run_refresh_wantlist_market_value(release_id),
            on_started=lambda: self._set_wantlist_actions_busy(True),
            on_finished=lambda: self._set_wantlist_actions_busy(False),
            on_success=self._apply_wantlist_pricing_refresh_result,
            on_error=self._handle_wantlist_action_error,
        )

    def _apply_wantlist_pricing_refresh_result(
        self, payload: dict[str, object]
    ) -> None:
        release_id = payload.get("discogs_release_id")
        selected = (
            dict(self._selected_wantlist)
            if isinstance(self._selected_wantlist, dict)
            else {}
        )
        if isinstance(release_id, int):
            selected["discogs_release_id"] = release_id
            self._selected_wantlist_id = release_id

        for key in (
            "market_lowest",
            "market_median",
            "market_highest",
            "market_currency",
            "market_last_updated_at",
        ):
            if key in payload:
                selected[key] = payload.get(key)

        self._selected_wantlist = dict(selected)
        self._wantlist_detail.set_entry(selected)
        release_id_text = str(release_id) if isinstance(release_id, int) else "n/a"
        self._set_status(f"Pricing refreshed for wantlist release {release_id_text}.")

    def _handle_browse_sync_clicked(self) -> None:
        self._start_async_action(
            action_key="browse-sync",
            busy_message="Syncing Discogs collection...",
            duplicate_message="Collection sync already in progress.",
            runner=lambda: run_sync_collection(
                progress_callback=self._make_sync_progress_callback("Syncing collection")
            ),
            on_success=self._apply_browse_sync_result,
            on_error=self._handle_release_load_error,
        )

    def _apply_browse_sync_result(self, payload: dict[str, object]) -> None:
        fetched = _to_int(payload.get("fetched_count"))
        upserted = _to_int(payload.get("upserted_count"))
        deactivated = _to_int(payload.get("deactivated_count"))
        self._set_status(
            f"Sync complete: fetched {fetched}, upserted {upserted}, deactivated {deactivated}."
        )
        self.load_releases(background=True)

    def _handle_wantlist_sync_clicked(self) -> None:
        self._start_async_action(
            action_key="wantlist-sync",
            busy_message="Syncing Discogs wantlist...",
            duplicate_message="Wantlist sync already in progress.",
            runner=lambda: run_sync_wantlist(
                progress_callback=self._make_sync_progress_callback("Syncing wantlist"),
                allow_empty_deactivate=False,
            ),
            on_success=self._apply_wantlist_sync_result,
            on_error=self._handle_wantlist_load_error,
        )

    def _apply_wantlist_sync_result(self, payload: dict[str, object]) -> None:
        fetched = _to_int(payload.get("fetched_count"))
        upserted = _to_int(payload.get("upserted_count"))
        deactivated = _to_int(payload.get("deactivated_count"))
        self._set_status(
            f"Wantlist sync complete: fetched {fetched}, upserted {upserted}, deactivated {deactivated}."
        )
        self.load_wantlist(background=True)

    def _handle_devices_refresh_clicked(self) -> None:
        self._start_async_action(
            action_key="device-action",
            busy_message="Refreshing Spotify devices...",
            duplicate_message="Device action already in progress.",
            runner=run_refresh_devices_action,
            on_started=lambda: self._set_device_actions_busy(True),
            on_finished=lambda: self._set_device_actions_busy(False),
            on_success=lambda payload: self._apply_device_action_payload(
                payload,
                default_message="Device list refreshed.",
            ),
            on_error=self._handle_device_action_error,
        )

    def _handle_set_default_device_clicked(self) -> None:
        try:
            selected_device_id = self._device_picker.selected_device_id()
            if not selected_device_id:
                raise ValueError("Select a device first.")
        except Exception as exc:
            self._handle_device_action_error(self._friendly_error_message(exc))
            return

        self._start_async_action(
            action_key="device-action",
            busy_message="Setting default Spotify device...",
            duplicate_message="Device action already in progress.",
            runner=lambda: run_set_default_device_action(selected_device_id),
            on_started=lambda: self._set_device_actions_busy(True),
            on_finished=lambda: self._set_device_actions_busy(False),
            on_success=lambda payload: self._apply_device_action_payload(
                payload,
                default_message="Default device updated.",
            ),
            on_error=self._handle_device_action_error,
        )

    def _handle_auto_select_device_clicked(self) -> None:
        self._start_async_action(
            action_key="device-action",
            busy_message="Auto-selecting default Spotify device...",
            duplicate_message="Device action already in progress.",
            runner=run_auto_set_default_device_action,
            on_started=lambda: self._set_device_actions_busy(True),
            on_finished=lambda: self._set_device_actions_busy(False),
            on_success=lambda payload: self._apply_device_action_payload(
                payload,
                default_message="Auto-selected default device.",
            ),
            on_error=self._handle_device_action_error,
        )

    def _apply_device_action_payload(
        self,
        payload: dict[str, object],
        *,
        default_message: str,
    ) -> None:
        devices_raw = payload.get("devices")
        devices = (
            [dict(item) for item in devices_raw if isinstance(item, dict)]
            if isinstance(devices_raw, list)
            else []
        )
        default_device_raw = payload.get("default_device")
        default_device = (
            dict(default_device_raw) if isinstance(default_device_raw, dict) else None
        )
        self._device_picker.set_devices(devices)
        self._device_picker.set_default_device(default_device)
        message = str(payload.get("status_message") or default_message)
        self._device_picker.set_result(message)
        self._set_status(message)

    def _handle_spin_clicked(self) -> None:
        try:
            filters = self._current_filters()
            seed = self._spin_wheel.get_seed()
        except Exception as exc:
            self._handle_spin_error(self._friendly_error_message(exc))
            return

        def on_started() -> None:
            self._pending_spin_result = None
            self._carousel.start_center_spin_animation()
            self._spin_wheel.start_spin_animation(
                on_complete=self._on_browse_spin_wheel_complete
            )

        started = self._start_async_action(
            action_key="browse-spin-action",
            busy_message="Spinning collection...",
            duplicate_message="Spin already in progress.",
            runner=lambda: run_spin_action(
                q=filters.get("q"),  # type: ignore[arg-type]
                year=filters.get("year"),  # type: ignore[arg-type]
                genres=filters.get("genres"),  # type: ignore[arg-type]
                styles=filters.get("styles"),  # type: ignore[arg-type]
                unmatched=bool(filters.get("unmatched", False)),
                seed=seed,
            ),
            on_started=on_started,
            on_success=self._handle_spin_payload_ready,
            on_error=self._handle_spin_error,
        )
        if not started:
            self._carousel.stop_center_spin_animation()

    def _handle_spin_payload_ready(self, payload: dict[str, object]) -> None:
        release_id_raw = payload.get("discogs_release_id")
        release_id: int | None = None
        if isinstance(release_id_raw, int):
            release_id = _to_int(release_id_raw)
        if not isinstance(release_id, int):
            release = payload.get("release")
            if isinstance(release, dict):
                release_candidate = release.get("discogs_release_id")
                if isinstance(release_candidate, int):
                    release_id = _to_int(release_candidate)

        self._pending_spin_result = payload
        self._carousel.set_spin_target_release(release_id)
        self._spin_wheel.complete_spin_animation(payload)

    def _apply_spin_result(self, payload: dict[str, object]) -> None:
        self._carousel.stop_center_spin_animation(invoke_callback=False)

        release = payload.get("release")
        if not isinstance(release, dict):
            release = payload

        release_id = release.get("discogs_release_id")
        if isinstance(release_id, int):
            quick_detail = self._release_with_cached_tracklist(release)
            self._selected_release_id = release_id
            self._selected_release = dict(quick_detail)
            self._album_detail.set_release(quick_detail)
            self._spin_wheel.set_context_release(quick_detail)

            GLib.idle_add(lambda: self._focus_release_id(release_id, allow_expand_limit=False) and False)

        self._set_status(str(payload.get("status_message") or "Spin complete."))

    def _on_browse_spin_wheel_complete(self, payload: dict[str, object]) -> None:
        self._pending_spin_result = None
        self._carousel.stop_center_spin_animation(invoke_callback=False)
        self._apply_spin_result(payload)

    def _handle_play_last_spin_clicked(self) -> None:
        self._start_async_action(
            action_key="spin-play-last",
            busy_message=(
                "Playing last spin..."
                if self._spotify_playback_available()
                else "Opening last spin in Spotify..."
            ),
            duplicate_message="Play last spin already in progress.",
            runner=run_play_last_spin_action,
            on_started=lambda: self._spin_wheel.set_controls_enabled(False),
            on_finished=lambda: self._spin_wheel.set_controls_enabled(True),
            on_success=self._apply_play_last_spin_result,
            on_error=self._handle_spin_error,
        )

    def _apply_play_last_spin_result(self, payload: dict[str, object]) -> None:
        raw = payload.get("raw")
        fallback_url = ""
        release_id: int | None = None
        if isinstance(raw, dict):
            fallback_url = str(raw.get("fallback_open_url") or "").strip()
            if isinstance(raw.get("discogs_release_id"), int):
                release_id = _to_int(raw.get("discogs_release_id"))

        if (
            not self._spotify_playback_available()
            and fallback_url
            and self._open_spotify_url(fallback_url)
        ):
            message = f"Opened in Spotify: {fallback_url}"
            self._spin_wheel.set_play_result({"status_message": message})
            self._set_status(message)
        else:
            self._spin_wheel.set_play_result(payload)
            self._set_status(
                str(payload.get("status_message") or "Play last spin complete.")
            )

        if release_id is not None:
            self._focus_release_id(release_id)

    def _handle_wantlist_spin_clicked(self) -> None:
        try:
            filters = self._current_wantlist_filters()
            seed = self._wantlist_spin_wheel.get_seed()
        except Exception as exc:
            self._handle_wantlist_spin_error(self._friendly_error_message(exc))
            return

        def on_started() -> None:
            self._wantlist_carousel.start_center_spin_animation()
            self._wantlist_spin_wheel.start_spin_animation(
                on_complete=self._apply_wantlist_spin_result
            )

        self._start_async_action(
            action_key="wantlist-spin-action",
            busy_message="Spinning wantlist...",
            duplicate_message="Wantlist spin already in progress.",
            runner=lambda: run_spin_wantlist(
                q=_as_optional_str(filters.get("q")),
                year=_as_optional_str(filters.get("year")),
                genres=_as_optional_str_list(filters.get("genres")),
                styles=_as_optional_str_list(filters.get("styles")),
                seed=seed,
            ),
            on_started=on_started,
            on_success=self._handle_wantlist_spin_payload_ready,
            on_error=self._handle_wantlist_spin_error,
        )

    def _handle_wantlist_spin_payload_ready(self, payload: dict[str, object]) -> None:
        release_id_raw = payload.get("discogs_release_id")
        release_id = (
            _to_int(release_id_raw)
            if isinstance(release_id_raw, int)
            else None
        )
        self._wantlist_carousel.set_spin_target_release(release_id)
        self._wantlist_spin_wheel.complete_spin_animation(payload)

    def _apply_wantlist_spin_result(self, payload: dict[str, object]) -> None:
        self._wantlist_carousel.stop_center_spin_animation()
        release_id = payload.get("discogs_release_id")
        if isinstance(release_id, int):
            # Immediately update the detail panel with spin result data
            # This avoids waiting for the full focus operation
            quick_detail = self._wantlist_with_cached_tracklist(payload)
            self._selected_wantlist_id = release_id
            self._selected_wantlist = dict(quick_detail)
            self._wantlist_detail.set_entry(quick_detail)
            self._wantlist_spin_wheel.set_context_release(quick_detail)

            # Try to focus in the carousel/text menu in the background
            # Use GLib.idle_add to not block the UI
            GLib.idle_add(lambda: self._focus_wantlist_id(release_id, allow_expand_limit=False) and False)

        artist = str(payload.get("artist") or "Unknown Artist")
        title = str(payload.get("title") or "Unknown Title")
        self._set_status(f"Wantlist spin selected: {artist} - {title}")

    def _handle_wantlist_spin_error(self, message: str) -> None:
        self._wantlist_spin_wheel.set_error(message)
        self._set_status(f"Wantlist spin error: {message}")

    def _handle_wantlist_play_last_spin_clicked(self) -> None:
        self._start_async_action(
            action_key="wantlist-play-last-spin",
            busy_message=(
                "Playing last wantlist spin..."
                if self._spotify_playback_available()
                else "Opening last wantlist spin in Spotify..."
            ),
            duplicate_message="Play last wantlist spin already in progress.",
            runner=lambda: self._run_play_last_wantlist_spin(),
            on_started=lambda: self._wantlist_spin_wheel.set_controls_enabled(False),
            on_finished=lambda: self._wantlist_spin_wheel.set_controls_enabled(True),
            on_success=self._apply_wantlist_play_last_spin_result,
            on_error=self._handle_wantlist_spin_error,
        )

    def _run_play_last_wantlist_spin(self) -> dict[str, object]:
        from discogs_player.core.settings import get_setting
        from discogs_player.data.db import get_connection
        from discogs_player.use_cases.play_release import run_play_release

        conn = get_connection()
        try:
            last_id = get_setting("last_spin_wantlist_id", conn=conn)
            if not last_id:
                return {
                    "ok": False,
                    "status_message": "No previous wantlist spin found.",
                }
            result = run_play_release(
                discogs_release_id=int(last_id),
                auto_match=True,
                open_fallback=True,
            )
            return {
                "ok": True,
                "status_message": result.get("message", "Playback started"),
                "raw": result,
            }
        finally:
            conn.close()

    def _apply_wantlist_play_last_spin_result(self, payload: dict[str, object]) -> None:
        message = str(payload.get("status_message") or "Play last wantlist spin complete.")
        raw = payload.get("raw")
        fallback_url = ""
        if isinstance(raw, dict):
            fallback_url = str(raw.get("fallback_open_url") or "").strip()
            release_id = raw.get("discogs_release_id")
            if isinstance(release_id, int):
                self._focus_wantlist_id(release_id)
        if (
            not self._spotify_playback_available()
            and fallback_url
            and self._open_spotify_url(fallback_url)
        ):
            opened_message = f"Opened in Spotify: {fallback_url}"
            self._wantlist_spin_wheel.set_play_result({"status_message": opened_message})
            self._set_status(opened_message)
            return

        self._wantlist_spin_wheel.set_play_result(payload)
        self._set_status(message)

    def load_wantlist(
        self,
        *,
        q: str | None = None,
        background: bool = True,
    ) -> dict[str, object]:
        return self.load_wantlist_with_filters(q=q, background=background)

    def load_wantlist_with_filters(
        self,
        *,
        q: str | None = None,
        year: str | None = None,
        genres: list[str] | None = None,
        styles: list[str] | None = None,
        sort_mode: str = "artist_title",
        limit: int | None = None,
        background: bool = True,
    ) -> dict[str, object]:
        preferred_release_id = self._selected_wantlist_id
        normalized_genres = list(genres or [])
        normalized_styles = list(styles or [])
        normalized_sort_mode = str(sort_mode or "artist_title")
        normalized_limit = _normalize_release_limit(limit)

        if not background:
            payload = self._run_wantlist_load_operation(
                q=q,
                year=year,
                genres=normalized_genres,
                styles=normalized_styles,
                sort_mode=normalized_sort_mode,
                limit=normalized_limit,
            )
            return self._apply_wantlist_load_result(
                payload,
                preferred_release_id=preferred_release_id,
            )

        def _on_success(payload: dict[str, object]) -> None:
            self._apply_wantlist_load_result(
                payload,
                preferred_release_id=preferred_release_id,
            )

        started = self._start_async_action(
            action_key="wantlist-load",
            busy_message="Loading wantlist...",
            duplicate_message="Wantlist load already in progress.",
            runner=lambda: self._run_wantlist_load_operation(
                q=q,
                year=year,
                genres=normalized_genres,
                styles=normalized_styles,
                sort_mode=normalized_sort_mode,
                limit=normalized_limit,
            ),
            on_success=_on_success,
            on_error=self._handle_wantlist_load_error,
        )
        return {
            "ok": bool(started),
            "scheduled": bool(started),
            "query": q,
            "year": year,
            "genres": normalized_genres,
            "styles": normalized_styles,
            "sort": normalized_sort_mode,
            "limit": normalized_limit,
        }

    def load_releases(
        self,
        *,
        q: str | None = None,
        background: bool = True,
    ) -> dict[str, object]:
        return self.load_releases_with_filters(q=q, background=background)

    def load_releases_with_filters(
        self,
        *,
        q: str | None = None,
        year: str | None = None,
        genres: list[str] | None = None,
        styles: list[str] | None = None,
        unmatched: bool = False,
        sort_mode: str = "artist_title",
        limit: int | None = None,
        background: bool = True,
    ) -> dict[str, object]:
        # Record startup t0 on the first call so _apply_release_load_result can
        # emit a [timing] startup-load line when --timing is active (item 6).
        if _TIMING_ENABLED and not hasattr(self, "_startup_load_t0"):
            self._startup_load_t0 = time.perf_counter()  # type: ignore[attr-defined]
        preferred_release_id = self._selected_release_id
        normalized_genres = list(genres or [])
        normalized_styles = list(styles or [])
        normalized_sort_mode = str(sort_mode or "artist_title")
        normalized_limit = _normalize_release_limit(limit)

        if not background:
            payload = self._run_release_load_operation(
                q=q,
                year=year,
                genres=normalized_genres,
                styles=normalized_styles,
                unmatched=unmatched,
                sort_mode=normalized_sort_mode,
                limit=normalized_limit,
            )
            return self._apply_release_load_result(
                payload,
                preferred_release_id=preferred_release_id,
            )

        def _on_success(payload: dict[str, object]) -> None:
            self._apply_release_load_result(
                payload,
                preferred_release_id=preferred_release_id,
            )

        started = self._start_async_action(
            action_key="browse-load",
            busy_message="Loading releases...",
            duplicate_message="Release load already in progress.",
            runner=lambda: self._run_release_load_operation(
                q=q,
                year=year,
                genres=normalized_genres,
                styles=normalized_styles,
                unmatched=unmatched,
                sort_mode=normalized_sort_mode,
                limit=normalized_limit,
            ),
            on_success=_on_success,
            on_error=self._handle_release_load_error,
        )
        return {
            "ok": bool(started),
            "scheduled": bool(started),
            "query": q,
            "year": year,
            "genres": normalized_genres,
            "styles": normalized_styles,
            "unmatched": unmatched,
            "sort": normalized_sort_mode,
            "limit": normalized_limit,
        }


class DiscogsPlayerApp(Adw.Application):
    def __init__(
        self,
        *,
        limit: int | None = None,
        preload_covers: bool = True,
        smoke_test: bool = False,
    ) -> None:
        super().__init__(application_id="com.discogs_player.app")
        self._limit = _normalize_release_limit(limit)
        self._preload_covers = bool(preload_covers)
        self._smoke_test = bool(smoke_test)
        self.exit_code = 0
        self._did_activate = False

    def do_activate(self) -> None:  # pragma: no cover - driven by integration runtime
        if self._did_activate:
            return
        self._did_activate = True

        report: dict[str, object]
        titlebar_present = False
        try:
            window = MainWindow(
                self, limit=self._limit, preload_covers=self._preload_covers
            )
            window.present()
            titlebar_present = bool(window.get_titlebar() is not None)
        except Exception as exc:
            self.exit_code = 1
            report = {
                "ok": False,
                "error": str(exc),
                "traceback": traceback.format_exc(limit=4),
                "titlebar_present": titlebar_present,
            }
            if self._smoke_test:
                print(json.dumps(report, sort_keys=True))
            self.quit()
            return

        try:
            report = window.load_releases(background=not self._smoke_test)
        except Exception as exc:
            self.exit_code = 1
            report = {
                "ok": False,
                "error": str(exc),
                "traceback": traceback.format_exc(limit=4),
            }
        report["titlebar_present"] = titlebar_present

        if self._smoke_test:
            print(json.dumps(report, sort_keys=True))
            self.quit()
            return

        GLib.idle_add(window._check_first_run)
