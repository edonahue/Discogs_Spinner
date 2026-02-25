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
    """Regression guard for wantlist/browse split reflow and fixed sidebar widths."""

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
    assert "GLib.timeout_add(120, self._apply_split_layout_from_current_size)" in content
    assert "def _handle_main_stack_changed(" in content
    assert "if self._active_main_view() == \"wantlist\":" in content
    assert "if self._active_main_view() == \"browse\":" in content

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
    """Test that window default size is more reasonable."""
    
    from pathlib import Path
    
    # Read the main_window.py file
    root_dir = Path(__file__).parents[1]
    main_window_file = root_dir / "src" / "discogs_player" / "ui" / "main_window.py"
    
    with open(main_window_file, 'r') as f:
        content = f.read()
    
    # Should have improved default size
    assert 'set_default_size(1200, 800)' in content  # Better default size
    assert 'set_size_request(900, 700)' in content  # Better minimum size
    
    print("✓ Better default window size")
    print("  Found set_default_size(1200, 800)")
    print("  Found set_size_request(900, 700)")


if __name__ == "__main__":
    try:
        test_responsive_css_present()
        test_window_resize_handlers_present()
        test_better_default_window_size()
        print("\n🎉 All window resizing improvements verified!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise
