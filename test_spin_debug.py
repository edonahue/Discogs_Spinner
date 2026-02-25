import sys
from unittest.mock import MagicMock

# Mock gi
mock_gi = MagicMock()
sys.modules['gi'] = mock_gi
sys.modules['gi.repository'] = MagicMock()
sys.modules['gi.repository.GLib'] = MagicMock()
sys.modules['gi.repository.Gtk'] = MagicMock()

# Mock Gtk.Box to be a real class we can inherit
class MockBox:
    def __init__(self, **kwargs): pass
    def set_margin_top(self, *args): pass
    def set_margin_bottom(self, *args): pass
    def set_margin_start(self, *args): pass
    def set_margin_end(self, *args): pass
    def set_halign(self, *args): pass
    def set_valign(self, *args): pass
    def set_hexpand(self, *args): pass
    def set_vexpand(self, *args): pass
    def add_css_class(self, *args): pass
    def append(self, *args): pass

sys.modules['gi.repository.Gtk'].Box = MockBox
sys.modules['gi.repository.Gtk'].Label = MagicMock()
sys.modules['gi.repository.Gtk'].Entry = MagicMock()
sys.modules['gi.repository.Gtk'].Button = MagicMock()
sys.modules['gi.repository.Gtk'].Orientation = MagicMock()

# Mock discogs_player.ui.utils.formatting
mock_fmt = MagicMock()
sys.modules['discogs_player.ui.utils.formatting'] = mock_fmt

# Import SpinWheel
sys.path.insert(0, 'src')
from discogs_player.ui.widgets.spin_wheel import SpinWheel

# Mock GLib timeout
callbacks = {}
next_id = 1

def mock_timeout_add(interval, callback, *args):
    global next_id
    sid = next_id
    next_id += 1
    callbacks[sid] = callback
    print(f"DEBUG: Added timeout source {sid}")
    return sid

def mock_source_remove(sid):
    if sid in callbacks:
        print(f"DEBUG: Removed timeout source {sid}")
        del callbacks[sid]

sys.modules['gi.repository.GLib'].timeout_add = mock_timeout_add
sys.modules['gi.repository.GLib'].source_remove = mock_source_remove

def tick_all():
    # Run a snapshot of callbacks
    current = list(callbacks.items())
    for sid, cb in current:
        if sid not in callbacks: continue
        res = cb()
        if not res:
            if sid in callbacks:
                print(f"DEBUG: Source {sid} returned False (finished)")
                del callbacks[sid]

def test_restart():
    wheel = SpinWheel()
    
    print("\n--- Spin 1 ---")
    wheel.start_spin_animation()
    if wheel._spin_source_id is None:
        print("FAIL: Spin 1 did not start")
        return
        
    # Run some ticks
    for _ in range(5): tick_all()
    
    # Complete
    print("Completing Spin 1...")
    wheel.complete_spin_animation({"release": {"title": "Album 1"}})
    
    # Run until finish
    print("Ticking until finish...")
    max_ticks = 100
    while max_ticks > 0 and wheel._spin_source_id is not None:
        tick_all()
        max_ticks -= 1
        
    if wheel._spin_source_id is not None:
        print("FAIL: Spin 1 did not clear source ID")
        return
    print("Spin 1 finished cleanly.")
    
    print("\n--- Spin 2 ---")
    wheel.start_spin_animation()
    if wheel._spin_source_id is None:
        print("FAIL: Spin 2 did not start (blocked?)")
        return
    print("PASS: Spin 2 started")

if __name__ == "__main__":
    try:
        test_restart()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
