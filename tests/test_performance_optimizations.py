"""Performance optimization tests for Discogs Player UI."""

import os
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest


def _headless_gtk_environment() -> bool:
    return not bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def test_virtualized_grid_performance():
    """Test virtualized grid performance characteristics."""
    if _headless_gtk_environment():
        pytest.skip("GTK performance test requires DISPLAY or WAYLAND_DISPLAY")

    try:
        from discogs_player.ui.performance import VirtualizedGrid
    except ImportError:
        pytest.skip("Performance module requires GTK dependencies")
        return
        
    # Mock item builder
    def mock_builder(item):
        label = Mock()
        label.get_text.return_value = item.get("title", "Unknown")
        return label
        
    with patch("gi.repository.GLib.idle_add") as mock_idle:
        mock_idle.side_effect = lambda f, *args, **kwargs: f(*args, **kwargs)
        
        grid = VirtualizedGrid(item_builder=mock_builder, viewport_size=25)
        # Replace internal grid with mock to avoid GTK type checking issues with Mock widgets
        grid._grid = Mock()
        grid._grid.get_first_child.return_value = None
        
        # Test with medium dataset
        items = [
            {"discogs_release_id": i, "title": f"Release {i}", "cover_url": f"http://example.com/cover{i}.jpg"}
            for i in range(100)
        ]
        
        start_time = time.time()
        grid.set_items(items)
        initial_render_time = time.time() - start_time
        
        # Test selection performance
        start_select = time.time()
        assert grid.select_by_id(50) is True
        select_time = time.time() - start_select
        
        # Test stats
        stats = grid.get_performance_stats()
        
        assert stats["total_items"] == 100
        assert stats["render_count"] >= 1  # Should have rendered at least once
        assert initial_render_time < 0.5  # Should be fast
        assert select_time < 0.1  # Selection should be very fast
        
        print("✓ VirtualizedGrid performance test passed")
        print(f"  Initial render: {initial_render_time*1000:.1f}ms")
        print(f"  Selection time: {select_time*1000:.1f}ms")
        print(f"  Render count: {stats['render_count']}")
    

def test_lazy_image_loader_performance():
    """Test lazy image loader performance and caching."""
    if _headless_gtk_environment():
        pytest.skip("GTK performance test requires DISPLAY or WAYLAND_DISPLAY")

    try:
        from discogs_player.ui.performance import LazyImageLoader
    except ImportError:
        pytest.skip("Performance module requires GTK dependencies")
        return
        
    loader = LazyImageLoader(max_concurrent_loads=2)
    
    # Mock the image cache to avoid network calls
    with patch('discogs_player.ui.performance.get_or_fetch_cover_path') as mock_cache:
        mock_cache.return_value = f"/fake/path/{hash('test')}.jpg"
        
        # Test loading performance
        callbacks = []
        def capture_callback(path, load_time):
            callbacks.append((path, load_time))
            
        start_time = time.time()
        
        # Load some images
        loader.load_image_async("http://example.com/cover1.jpg", capture_callback, priority=1)
        loader.load_image_async("http://example.com/cover2.jpg", capture_callback, priority=0)
        loader.load_image_async("http://example.com/cover3.jpg", capture_callback, priority=2)
        
        # Wait for async completion
        time.sleep(0.1)
        
        # Test cache stats
        stats = loader.get_cache_stats()
        
        assert len(callbacks) >= 2  # At least 2 callbacks
        assert stats["cached_images"] >= 1  # Should have cached something
        # With 0.1s wait and simulated delays < 0.05s, all 3 should complete
        assert stats["cache_efficiency"] == "3/3"
        
        total_time = time.time() - start_time
        
        print("✓ LazyImageLoader performance test passed")
        print(f"  Total time: {total_time*1000:.1f}ms")
        print(f"  Cache efficiency: {stats['cache_efficiency']}")
        

def test_performance_monitor():
    """Test performance monitoring functionality."""
    if _headless_gtk_environment():
        pytest.skip("GTK performance test requires DISPLAY or WAYLAND_DISPLAY")

    try:
        from discogs_player.ui.performance import PerformanceMonitor
    except ImportError:
        pytest.skip("Performance module requires GTK dependencies")
        return
        
    monitor = PerformanceMonitor()
    
    # Simulate some performance data
    monitor.record_render_time(45.2)
    monitor.record_scroll_response(23.1)
    monitor.record_image_load(120.5)
    monitor.record_image_load(89.3)
    monitor.record_navigation(15.7)
    
    report = monitor.get_performance_report()
    
    assert report["uptime_seconds"] > 0
    assert "metrics" in report
    assert "recommendations" in report
    
    # Check metric analysis
    render_stats = report["metrics"]["render_time"]
    assert render_stats["avg"] == 45.2
    assert render_stats["min"] == 45.2
    assert render_stats["max"] == 45.2
    
    print("✓ PerformanceMonitor test passed")
    print(f"  Recommendations: {report['recommendations']}")
    

def test_image_cache_optimization():
    """Test image cache optimization improvements."""
    
    # Add performance module to path
    root_dir = Path(__file__).parents[1]
    perf_file = root_dir / "src" / "discogs_player" / "ui" / "performance.py"
    
    assert perf_file.exists(), "Performance module should exist"
    
    # Check for performance improvements
    with open(perf_file, 'r') as f:
        content = f.read()
        
    # Should contain new performance classes
    assert "VirtualizedGrid" in content
    assert "LazyImageLoader" in content
    assert "PerformanceMonitor" in content
    assert "viewport_size" in content, "Should have viewport optimization"
    assert "debounce" in content, "Should have scroll debouncing"
    assert "in_flight_info.get(\"future\")" in content
    assert "sleep_delay = max(0.0" in content
    assert "normalized_radius = max(0, int(radius))" in content
    assert "current_index + normalized_radius + 1" in content
    
    print("✓ Image cache optimization test passed")
    print("  Found VirtualizedGrid class")
    print("  Found LazyImageLoader class") 
    print("  Found PerformanceMonitor class")
    print("  Contains viewport optimization")
    print("  Contains scroll debouncing")


def test_main_window_timing_infrastructure_present():
    """Verify that per-operation timing hooks exist in main_window.py.

    Hotspot 1: run_browse_release_grid / run_browse_wantlist_grid query time.
    Hotspot 2: sort_release_items time.
    Hotspot 3: widget bulk-population time (main thread).

    The hooks record elapsed times via time.perf_counter() and include them in
    the return dicts (_timing_query_s, _timing_sort_s).  set_timing_enabled()
    gates stderr output.
    """
    root_dir = Path(__file__).parents[1]
    mw_file = root_dir / "src" / "discogs_player" / "ui" / "main_window.py"
    assert mw_file.exists(), "main_window.py not found"

    src = mw_file.read_text()

    assert "import time" in src, "time module must be imported"
    assert "_TIMING_ENABLED" in src, "_TIMING_ENABLED module flag must be present"
    assert "set_timing_enabled" in src, "set_timing_enabled() function must be present"
    assert "_timing_query_s" in src, "Hotspot-1 timing key must be in return dict"
    assert "_timing_sort_s" in src, "Hotspot-2 timing key must be in return dict"
    assert "[timing] browse-load" in src, "browse-load timing print must be present"
    assert "[timing] wantlist-load" in src, "wantlist-load timing print must be present"


def test_ui_main_timing_flag_present():
    """Verify --timing CLI argument is wired up in ui_main.py."""
    root_dir = Path(__file__).parents[1]
    ui_main_file = root_dir / "src" / "discogs_player" / "ui_main.py"
    assert ui_main_file.exists(), "ui_main.py not found"

    src = ui_main_file.read_text()
    assert "--timing" in src, "--timing argument must be declared in ui_main.py"
    assert "set_timing_enabled" in src, "set_timing_enabled must be called in ui_main.py"


def test_main_window_empty_state_messages_use_plain_quotes():
    """Empty-state status messages must use plain quotes, not shell backticks.

    GTK status labels render backticks literally; plain quotes are cleaner
    in a GUI context.
    """
    root_dir = Path(__file__).parents[1]
    mw_file = root_dir / "src" / "discogs_player" / "ui" / "main_window.py"
    src = mw_file.read_text()

    assert "Run `dplayer sync`" not in src, (
        "Empty-state message must not use backtick-quoted CLI commands"
    )
    assert "Run `dplayer wantlist sync`" not in src, (
        "Empty-state wantlist message must not use backtick-quoted CLI commands"
    )


if __name__ == "__main__":
    test_virtualized_grid_performance()
    test_lazy_image_loader_performance()
    test_performance_monitor()
    test_image_cache_optimization()
    test_main_window_timing_infrastructure_present()
    test_ui_main_timing_flag_present()
    test_main_window_empty_state_messages_use_plain_quotes()
    print("\n🎉 All performance tests passed!")
