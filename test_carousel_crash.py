import sys
from unittest.mock import MagicMock

# Mock gi
mock_gi = MagicMock()
sys.modules['gi'] = mock_gi
sys.modules['gi.repository'] = MagicMock()
sys.modules['gi.repository.GLib'] = MagicMock()
sys.modules['gi.repository.Gtk'] = MagicMock()

# Mock Gtk classes
class MockWidget:
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
    def set_size_request(self, *args): pass
    def add_controller(self, *args): pass
    def set_child(self, *args): pass
    def set_pixel_size(self, *args): pass
    def set_sensitive(self, *args): pass
    def connect(self, *args): pass
    def set_text(self, *args): pass

class MockFrame(MockWidget): pass
class MockBox(MockWidget): pass
class MockButton(MockWidget): pass
class MockLabel(MockWidget): pass
class MockImage(MockWidget):
    def get_paintable(self): return None
    @classmethod
    def new_from_icon_name(cls, *args): return MockImage()

class MockPicture(MockWidget):
    def set_can_shrink(self, *args): pass
    def set_content_fit(self, *args): pass
    @classmethod
    def new_for_filename(cls, *args): return MockPicture()

class MockGestureClick(MockWidget):
    @classmethod
    def new(cls): return MockGestureClick()

sys.modules['gi.repository.Gtk'].Box = MockBox
sys.modules['gi.repository.Gtk'].Frame = MockFrame
sys.modules['gi.repository.Gtk'].Button = MockButton
sys.modules['gi.repository.Gtk'].Label = MockLabel
sys.modules['gi.repository.Gtk'].Image = MockImage
sys.modules['gi.repository.Gtk'].Picture = MockPicture
sys.modules['gi.repository.Gtk'].GestureClick = MockGestureClick
sys.modules['gi.repository.Gtk'].Orientation = MagicMock()
sys.modules['gi.repository.Gtk'].Align = MagicMock()
sys.modules['gi.repository.Gtk'].ContentFit = MagicMock()

# Mock image cache
mock_img = MagicMock()
mock_img.get_or_fetch_cover_path = MagicMock(return_value=None)
sys.modules['discogs_player.services.image_cache'] = mock_img

# Import CoverCarousel
sys.path.insert(0, 'src')
from discogs_player.ui.widgets.cover_carousel import CoverCarousel

# Mock GLib timeout
callbacks = {}
next_id = 1

def mock_timeout_add(interval, callback, *args):
    global next_id
    sid = next_id
    next_id += 1
    callbacks[sid] = callback
    return sid

def mock_source_remove(sid):
    if sid in callbacks:
        del callbacks[sid]

sys.modules['gi.repository.GLib'].timeout_add = mock_timeout_add
sys.modules['gi.repository.GLib'].source_remove = mock_source_remove

def tick_all():
    current = list(callbacks.items())
    for sid, cb in current:
        if sid not in callbacks: continue
        res = cb()
        if not res:
            if sid in callbacks:
                del callbacks[sid]

def test_carousel_crash():
    carousel = CoverCarousel()
    items = [
        {"discogs_release_id": i, "title": f"R{i}", "cover_url": f"http://u{i}"}
        for i in range(10)
    ]
    carousel.set_items(items)
    
    print("\n--- Spin 1 ---")
    carousel.start_center_spin_animation()
    if carousel._center_spin_source_id is None:
        print("FAIL: Spin 1 did not start")
        return
        
    # Tick for a while
    for _ in range(20): tick_all()
    
    # Set target
    carousel.set_spin_target_release(5)
    
    # Tick until finish
    max_ticks = 100
    while max_ticks > 0 and carousel._center_spin_source_id is not None:
        tick_all()
        max_ticks -= 1
        
    if carousel._center_spin_source_id is not None:
        print("FAIL: Spin 1 did not finish")
    else:
        print("Spin 1 finished.")
        
    print("\n--- Spin 2 ---")
    carousel.start_center_spin_animation()
    if carousel._center_spin_source_id is None:
        print("FAIL: Spin 2 did not start")
        return
        
    # Tick - this is where it allegedly fails
    print("Ticking Spin 2...")
    initial_id = carousel._center_spin_source_id
    tick_all()
    
    if carousel._center_spin_source_id is None:
        print("FAIL: Spin 2 stopped immediately (crashed?)")
    else:
        print("PASS: Spin 2 running")

if __name__ == "__main__":
    try:
        test_carousel_crash()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
