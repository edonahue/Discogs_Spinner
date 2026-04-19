"""Test improvements to window resizing and responsive design."""



def test_responsive_css_present():
    """Test that responsive CSS rules are present."""
    
    # Import CSS directly without importing the main window (to avoid GTK dependencies)
    from pathlib import Path
    
    # Read the main_window.py file and extract CSS
    root_dir = Path(__file__).parents[1]
    main_window_file = root_dir / "src" / "discogs_player" / "ui" / "main_window.py"
    
    with open(main_window_file, 'r') as f:
        content = f.read()
    
    # Extract CSS content
    css_start = content.find('_IPOD_NANO_CSS = """')
    css_end = content.find('"""', css_start + 20)
    css = content[css_start:css_end + 3]
    
    # Check for responsive design elements
    assert ".ipod-root {" in css  # Minimum window size
    assert "min-width: 800px" in css  # Minimum window width
    assert "min-height: 600px" in css  # Minimum window height
    
    # Check for responsive class selectors
    assert ".ipod-root.ipod-width-compact" in css  # Responsive design
    assert ".ipod-root.ipod-width-ultra-compact" in css  # Small screens
    
    print("✓ Responsive CSS rules are present")
    print("  Found minimum window size")
    print("  Found responsive class selectors")


def test_window_resize_handlers_present():
    """Test that proper window resize handlers are present."""
    
    from pathlib import Path
    
    # Read the main_window.py file
    root_dir = Path(__file__).parents[1]
    main_window_file = root_dir / "src" / "discogs_player" / "ui" / "main_window.py"
    
    with open(main_window_file, 'r') as f:
        content = f.read()
    
    # Check for proper GTK4 resize handling
    assert 'connect(\'notify::default-width\'' in content  # GTK4 proper resize handling
    assert 'connect(\'notify::default-height\'' in content  # GTK4 proper resize handling
    assert 'def _on_window_resize(' in content  # Resize handler
    assert 'def _on_window_state_change(' in content  # State change handler
    
    # Check that EventControllerMotion resize signal is NOT present (the bug)
    assert 'EventControllerMotion' not in content or 'resize' not in content.split('EventControllerMotion')[1].split('\n')[0]
    
    print("✓ Proper GTK4 window resize handlers are present")
    print("  Found notify::default-width connection")
    print("  Found notify::default-height connection")
    print("  Found _on_window_resize method")
    print("  Found _on_window_state_change method")


def test_split_layout_ratio_logic_present():
    """Test that browse/wantlist paned split uses shared responsive ratio logic."""

    from pathlib import Path

    root_dir = Path(__file__).parents[1]
    main_window_file = root_dir / "src" / "discogs_player" / "ui" / "main_window.py"

    content = main_window_file.read_text(encoding="utf-8")

    assert "_DETAIL_PANEL_WIDTH_RATIO =" in content
    assert "self._wantlist_content = wantlist_content" in content
    assert "self._browse_content = content" in content
    assert "def _effective_layout_width(" in content
    assert "def _compute_detail_panel_width(" in content
    assert "def _apply_split_layout(" in content
    assert "def _sync_carousel_layout_hints(" in content
    assert "def _on_stack_size_change(" in content
    assert 'self._browse_stack.connect("notify::width", self._on_stack_size_change)' in content
    assert 'self._wantlist_stack.connect("notify::width", self._on_stack_size_change)' in content
    assert "self._carousel.apply_layout_hint(" in content
    assert "self._wantlist_carousel.apply_layout_hint(" in content
    assert "self._browse_content.set_position(" in content
    assert "self._wantlist_content.set_position(" in content

    print("✓ Shared split layout ratio logic is present")


def test_split_layout_reflow_guards_present():
    """Regression guard for startup/maximize/tab-return reflow orchestration."""

    from pathlib import Path

    root_dir = Path(__file__).parents[1]
    main_window_file = root_dir / "src" / "discogs_player" / "ui" / "main_window.py"
    content = main_window_file.read_text(encoding="utf-8")

    assert "self._sidebar_scroll.set_max_content_width(browse_detail_width)" in content
    assert "self._wantlist_sidebar_scroll.set_max_content_width(" in content
    assert "self._sidebar_scroll.set_size_request(browse_detail_width, -1)" in content
    assert "self._wantlist_sidebar_scroll.set_size_request(wantlist_detail_width, -1)" in content
    assert "self._sidebar_scroll.set_propagate_natural_width(False)" in content
    assert "self._wantlist_sidebar_scroll.set_propagate_natural_width(False)" in content
    assert "_VISIBLE_LAYOUT_SETTLE_DELAYS_MS = (0, 90, 220, 420)" in content
    assert "self._layout_settle_source_ids: dict[str, int] = {}" in content
    assert "def _cancel_visible_layout_settle(self) -> None:" in content
    assert "def _visible_layout_ready_for_reflow(self, active_view: str) -> bool:" in content
    assert "def _run_visible_layout_settle_pass(" in content
    assert "def _schedule_visible_layout_settle(self, *, reason: str) -> None:" in content
    assert "def _handle_main_stack_changed(" in content
    assert 'active_view = self._active_main_view()' in content
    assert 'elif active_view == "wantlist":' in content
    assert 'if active_view == "browse":' in content
    assert 'self._schedule_visible_layout_settle(reason="startup")' in content
    assert 'self._schedule_visible_layout_settle(reason="window-resize")' in content
    assert 'self._schedule_visible_layout_settle(reason="window-state")' in content
    assert 'self._schedule_visible_layout_settle(reason="main-stack-changed")' in content
    assert 'self._schedule_visible_layout_settle(reason="browse-load")' in content
    assert 'self._schedule_visible_layout_settle(reason="wantlist-load")' in content

    print("✓ Split layout reflow guards are present")


def test_split_layout_resets_scrolled_max_width_before_min_width_updates():
    """Guard against GTK warning when min width is set while max is stale."""

    from pathlib import Path

    root_dir = Path(__file__).parents[1]
    main_window_file = root_dir / "src" / "discogs_player" / "ui" / "main_window.py"
    content = main_window_file.read_text(encoding="utf-8")

    assert "self._sidebar_scroll.set_max_content_width(-1)" in content
    assert "self._wantlist_sidebar_scroll.set_max_content_width(-1)" in content
    assert "self._sidebar_scroll.set_min_content_width(browse_detail_width)" in content
    assert (
        "self._wantlist_sidebar_scroll.set_min_content_width(wantlist_detail_width)"
        in content
    )

    print("✓ Split layout width ordering guard is present")


def test_better_default_window_size():
    """Test that startup window sizing is monitor-aware and less aggressive."""
    
    from pathlib import Path
    
    # Read the main_window.py file
    root_dir = Path(__file__).parents[1]
    main_window_file = root_dir / "src" / "discogs_player" / "ui" / "main_window.py"
    
    with open(main_window_file, 'r') as f:
        content = f.read()
    
    assert "_STARTUP_WINDOW_DEFAULT_WIDTH = 1100" in content
    assert "_STARTUP_WINDOW_DEFAULT_HEIGHT = 760" in content
    assert "_STARTUP_WINDOW_MIN_WIDTH = 820" in content
    assert "_STARTUP_WINDOW_MIN_HEIGHT = 620" in content
    assert "def _startup_target_window_size(self) -> tuple[int, int]:" in content
    assert "def _apply_startup_window_size(self) -> bool:" in content
    assert "self.set_default_size(target_width, target_height)" in content
    assert "self.queue_resize()" in content

    print("✓ Better default window size")
    print("  Found monitor-aware startup sizing helpers")
    print("  Found smaller startup and minimum window targets")


if __name__ == "__main__":
    try:
        test_responsive_css_present()
        test_window_resize_handlers_present()
        test_better_default_window_size()
        print("\n🎉 All window resizing improvements verified!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise
