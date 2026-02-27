"""UI Performance optimizations for Discogs Player.

Status: DEFERRED (Phase 2 close, 2026-02-26)

VirtualizedGrid, LazyImageLoader, and PerformanceMonitor were pre-built
for a future virtualization pass. They are not wired into the live app yet.
The active timing infrastructure lives in main_window.py (_TIMING_ENABLED,
set_timing_enabled(), --timing CLI flag).

Integration path: Phase 3 or later, contingent on pilot timing run results.
If widget-population latency (Hotspot 3) exceeds ~200ms for typical
collection sizes, VirtualizedGrid is the candidate replacement for the
FlowBox grid in CoverGrid.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib

from discogs_player.services.image_cache import get_or_fetch_cover_path


class VirtualizedGrid(Gtk.ScrolledWindow):
    """
    A virtualized grid widget that efficiently renders large datasets.

    Uses a viewport with limited number of children to avoid creating
    thousands of widgets for large collections.
    """

    def __init__(
        self,
        *,
        item_builder: Callable[[dict[str, Any]], Gtk.Widget],
        on_selection_changed: Callable[[dict[str, Any] | None], None] | None = None,
        viewport_size: int = 50,  # Number of items to render at once
    ) -> None:
        super().__init__()
        self.set_vexpand(True)
        self.set_hexpand(True)

        self._item_builder = item_builder
        self._on_selection_changed = on_selection_changed
        self._viewport_size = viewport_size
        self._items: list[dict[str, Any]] = []
        self._visible_start = 0
        self._selected_id: int | None = None

        # Performance tracking
        self._render_count = 0
        self._last_render_time = 0.0

        # Create viewport with efficient scrolling
        self._viewport = Gtk.Viewport()
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        # Grid for efficient layout
        self._grid = Gtk.Grid()
        self._grid.set_row_spacing(8)
        self._grid.set_column_spacing(8)
        self._grid.set_margin_top(8)
        self._grid.set_margin_bottom(8)
        self._grid.set_margin_start(8)
        self._grid.set_margin_end(8)

        self._viewport.set_child(self._grid)
        self.set_child(self._viewport)

        # Connect scroll events for virtualization
        self._vadj = self._viewport.get_vadjustment()
        self._vadj.connect("value-changed", self._on_scroll)

        # Track scroll performance
        self._scroll_debounce_id = None

    def _on_scroll(self, adjustment) -> None:
        """Handle scroll events with debouncing for performance."""
        # Cancel existing debounce
        if self._scroll_debounce_id:
            GLib.source_remove(self._scroll_debounce_id)

        # Debounce scroll events to avoid excessive re-rendering
        self._scroll_debounce_id = GLib.timeout_add(
            50,  # 50ms debounce
            self._update_visible_range,
            priority=GLib.PRIORITY_DEFAULT_IDLE,
        )

    def _update_visible_range(self) -> None:
        """Update visible range based on scroll position."""
        if not self._items:
            return

        viewport_height = self._viewport.get_allocated_height()
        item_height = 280  # Approximate item height
        visible_count = min(self._viewport_size, viewport_height // item_height + 5)

        start_idx = int(self._vadj.get_value() // item_height)
        start_idx = max(0, start_idx - 5)  # Small buffer above
        end_idx = min(len(self._items), start_idx + visible_count + 5)  # Small buffer below

        if start_idx != self._visible_start or (end_idx - start_idx) != visible_count:
            self._render_visible_items(start_idx, end_idx)
            self._visible_start = start_idx

    def _render_visible_items(self, start_idx: int, end_idx: int) -> None:
        """Render only visible items for performance."""
        start_time = time.time()

        # Clear existing children efficiently
        child = self._grid.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self._grid.remove(child)
            child = next_child

        # Render visible items
        visible_items = self._items[start_idx:end_idx]
        for i, item in enumerate(visible_items):
            widget = self._item_builder(item)
            row = i // 5  # 5 columns
            col = i % 5
            self._grid.attach(widget, col, row, 1, 1)

        self._render_count += 1
        self._last_render_time = time.time() - start_time

    def set_items(self, items: list[dict[str, Any]]) -> None:
        """Set items and trigger efficient re-render."""
        self._items = items
        self._visible_start = 0
        self._selected_id = None

        # Trigger initial render
        GLib.idle_add(self._update_visible_range)

    def get_selected_item(self) -> dict[str, Any] | None:
        """Get currently selected item."""
        if self._selected_id is None:
            return None
        for item in self._items:
            if item.get("discogs_release_id") == self._selected_id:
                return item
        return None

    def get_performance_stats(self) -> dict[str, Any]:
        """Get performance statistics for monitoring."""
        return {
            "total_items": len(self._items),
            "visible_range": f"{self._visible_start}-{self._visible_start + self._viewport_size}",
            "render_count": self._render_count,
            "last_render_time_ms": self._last_render_time * 1000,
        }

    def select_by_id(self, item_id: int) -> bool:
        """Select item by ID efficiently."""
        if not any(item.get("discogs_release_id") == item_id for item in self._items):
            return False

        self._selected_id = item_id
        # Update selection highlighting would go here in a full implementation
        return True


class LazyImageLoader:
    """
    Efficient image loading with lazy loading and caching.

    Loads images progressively and provides smooth transitions.
    """

    def __init__(self, max_concurrent_loads: int = 3) -> None:
        self._max_concurrent_loads = max_concurrent_loads
        self._loading_cache: dict[str, tuple[str | None, float]] = {}  # url -> (path, load_time)
        self._in_flight: dict[str, Any] = {}
        self._executor = ThreadPoolExecutor(
            max_workers=max_concurrent_loads,
            thread_name_prefix="lazy-image-loader",
        )

    def load_image_async(
        self,
        image_url: str,
        callback: Callable[[str | None, float], None],
        *,
        priority: int = 0,  # Higher priority = load sooner
    ) -> None:
        """Load image asynchronously with priority and caching."""
        if not image_url:
            callback(None, 0.0)
            return

        # Check cache first
        cached = self._loading_cache.get(image_url)
        if cached:
            callback(cached[0], cached[1])
            return

        # Cancel lower priority requests for same image
        to_cancel = [
            url for url, info in self._in_flight.items()
            if url == image_url and info.get("priority", 0) < priority
        ]
        for url in to_cancel:
            in_flight_info = self._in_flight.get(url)
            future = (
                in_flight_info.get("future")
                if isinstance(in_flight_info, dict)
                else None
            )
            if future and hasattr(future, "cancel"):
                future.cancel()

        # Submit new request
        future = self._executor.submit(self._load_image_worker, image_url, priority)
        self._in_flight[image_url] = {"future": future, "priority": priority}

        # Handle completion
        def on_done(fut):
            if fut.cancelled():
                return
            try:
                result = fut.result()
                self._loading_cache[image_url] = (result, time.time())
                callback(result, time.time())
            except Exception:
                callback(None, time.time())
            finally:
                self._in_flight.pop(image_url, None)

        future.add_done_callback(on_done)

    def _load_image_worker(self, image_url: str, priority: int) -> str | None:
        """Worker function for loading images."""
        # Simulate priority-based loading (in real implementation, could use network priority)
        sleep_delay = max(0.0, 0.01 * (5 - priority))  # Higher priority = less delay
        time.sleep(sleep_delay)

        try:
            return get_or_fetch_cover_path(image_url)
        except Exception:
            return None

    def preload_nearby(self, current_index: int, all_urls: list[str], radius: int = 3) -> None:
        """Preload images near current position."""
        normalized_radius = max(0, int(radius))
        start = max(0, current_index - normalized_radius)
        end = min(len(all_urls), current_index + normalized_radius + 1)

        for url in all_urls[start:end]:
            if url not in self._loading_cache and url not in self._in_flight:
                # Lower priority for preloads
                self.load_image_async(url, lambda path, t: None, priority=-1)

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics for monitoring."""
        total_cached = len(self._loading_cache)
        total_in_flight = len(self._in_flight)

        # Calculate cache hit rate
        cache_hits = sum(1 for info in self._loading_cache.values() if info[0] is not None)

        return {
            "cached_images": total_cached,
            "in_flight_loads": total_in_flight,
            "cache_hit_rate": cache_hits / max(1, total_cached + total_in_flight) if total_cached > 0 else 0,
            "cache_efficiency": f"{total_cached}/{total_cached + total_in_flight}",
        }


class PerformanceMonitor:
    """
    Monitor UI performance metrics and provide optimization suggestions.
    """

    def __init__(self) -> None:
        self._metrics: dict[str, list[float]] = {
            "render_time": [],
            "scroll_response": [],
            "image_load_time": [],
            "navigation_time": [],
        }
        self._start_time = time.time()

    def record_render_time(self, duration_ms: float) -> None:
        """Record UI render time."""
        self._metrics["render_time"].append(duration_ms)

    def record_scroll_response(self, response_ms: float) -> None:
        """Record scroll response time."""
        self._metrics["scroll_response"].append(response_ms)

    def record_image_load(self, load_time_ms: float) -> None:
        """Record image loading time."""
        self._metrics["image_load_time"].append(load_time_ms)

    def record_navigation(self, action_time_ms: float) -> None:
        """Record navigation action time."""
        self._metrics["navigation_time"].append(action_time_ms)

    def get_performance_report(self) -> dict[str, Any]:
        """Get comprehensive performance report."""
        current_time = time.time()
        uptime = current_time - self._start_time

        return {
            "uptime_seconds": uptime,
            "metrics": {
                name: self._analyze_times(times)
                for name, times in self._metrics.items()
            },
            "recommendations": self._generate_recommendations(),
        }

    @staticmethod
    def _analyze_times(times: list[float]) -> dict[str, float]:
        if not times:
            return {"avg": 0, "min": 0, "max": 0, "p95": 0}
        sorted_times = sorted(times)
        return {
            "avg": sum(times) / len(times),
            "min": sorted_times[0],
            "max": sorted_times[-1],
            "p95": sorted_times[int(len(times) * 0.95)] if len(times) > 20 else sorted_times[-1],
        }

    def _generate_recommendations(self) -> list[str]:
        """Generate performance recommendations based on metrics."""
        recommendations = []

        render_stats = self._analyze_times(self._metrics["render_time"])
        if render_stats["avg"] > 100:  # >100ms render time
            recommendations.append("Consider reducing visible items in grid")

        scroll_stats = self._analyze_times(self._metrics["scroll_response"])
        if scroll_stats["avg"] > 50:  # >50ms scroll response
            recommendations.append("Increase scroll debounce time")

        image_stats = self._analyze_times(self._metrics["image_load_time"])
        if image_stats["avg"] > 500:  # >500ms image load
            recommendations.append("Implement more aggressive image preloading")

        if not recommendations:
            recommendations.append("Performance is optimal")

        return recommendations


def install_performance_monitoring(app) -> PerformanceMonitor:
    """Install performance monitoring for the application."""
    monitor = PerformanceMonitor()

    # Hook into key application events
    original_present = app.do_activate

    def monitored_present():
        start = time.time()
        try:
            original_present()
        finally:
            duration = (time.time() - start) * 1000
            monitor.record_navigation(duration)

    app.do_activate = monitored_present

    return monitor


# Export key classes for easy import
__all__ = [
    "VirtualizedGrid",
    "LazyImageLoader",
    "PerformanceMonitor",
    "install_performance_monitoring",
]
