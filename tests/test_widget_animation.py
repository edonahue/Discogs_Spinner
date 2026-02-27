"""Behavior tests for CoverCarousel and SpinWheel animation state machines.

These tests exercise the GLib timeout-driven animation loops by replacing
GLib.timeout_add / source_remove with a synchronous tick registry, allowing
animation logic to run deterministically without a live GTK main loop.

This module replaces the root-level scratch scripts:
  - test_carousel_crash.py
  - test_spin_debug.py
  - reproduce_carousel_spin.py
"""

from __future__ import annotations

import sys
import types

import pytest

# ============================================================
# Minimal GTK stand-in classes
# ============================================================


class _MockWidget:
    """Base stand-in for any GTK widget used in animation code."""

    def __init__(self, *a, **kw):
        pass

    def __getattr__(self, name):
        # Any unresolved GTK method call is a harmless no-op.
        return lambda *a, **kw: None


class _GenericGtkClass:
    """Stand-in for a GTK class that is only ever instantiated (not subclassed).

    Each call returns a fresh _MockWidget.  Classmethod-style calls like
    Gtk.Image.new_from_icon_name(...) also return _MockWidget via __getattr__.
    """

    def __call__(self, *a, **kw):
        return _MockWidget()

    def __getattr__(self, name):
        return lambda *a, **kw: _MockWidget()


_generic = _GenericGtkClass()


class _GtkModule:
    """Fake gi.repository.Gtk module."""

    # Must be a real class: CoverCarousel and SpinWheel inherit from Gtk.Box.
    Box = _MockWidget

    # Instantiated-only widgets — each call returns a fresh _MockWidget.
    Label = _generic
    Button = _generic
    Frame = _generic
    Image = _generic
    Picture = _generic
    GestureClick = _generic
    Entry = _generic
    ToggleButton = _generic
    ScrolledWindow = _generic
    Stack = _generic
    HeaderBar = _generic
    SpinButton = _generic
    Spinner = _generic
    Grid = _generic
    Revealer = _generic
    LinkButton = _generic

    # Enum-like namespaces — attribute access returns a sentinel value.
    class Orientation:
        VERTICAL = "vertical"
        HORIZONTAL = "horizontal"

    class Align:
        START = "start"
        END = "end"
        CENTER = "center"
        FILL = "fill"

    class ContentFit:
        COVER = "cover"

    class PolicyType:
        AUTOMATIC = "automatic"
        NEVER = "never"

    def __getattr__(self, name):
        # Any other Gtk class not listed above falls back to _generic.
        return _generic


class _GLibModule:
    """Fake gi.repository.GLib with a synchronous callback registry."""

    # These are replaced below after module-level registry is defined.
    timeout_add = None
    source_remove = None

    @staticmethod
    def idle_add(f, *a):
        pass  # deferred calls are no-ops in tests


class _GdkModule:
    class Texture:
        @staticmethod
        def new_from_file(*a):
            return _MockWidget()

    def __getattr__(self, name):
        return _generic


class _GioModule:
    class File:
        @staticmethod
        def new_for_path(*a):
            return _MockWidget()

    def __getattr__(self, name):
        return _generic


# ============================================================
# Seed sys.modules before any widget import
# ============================================================

_gtk_mod = _GtkModule()
_glib_mod = _GLibModule()
_gdk_mod = _GdkModule()
_gio_mod = _GioModule()

# gi top-level — only needs to absorb gi.require_version(...)
_gi_top = types.ModuleType("gi")
_gi_top.require_version = lambda *a, **kw: None
sys.modules["gi"] = _gi_top

# gi.repository must be a real module so `from gi.repository import GLib`
# resolves to our objects, not MagicMock auto-attributes.
_gi_repo = types.ModuleType("gi.repository")
_gi_repo.Gtk = _gtk_mod
_gi_repo.GLib = _glib_mod
_gi_repo.Gdk = _gdk_mod
_gi_repo.Gio = _gio_mod
sys.modules["gi.repository"] = _gi_repo
sys.modules["gi.repository.Gtk"] = _gtk_mod
sys.modules["gi.repository.GLib"] = _glib_mod
sys.modules["gi.repository.Gdk"] = _gdk_mod
sys.modules["gi.repository.Gio"] = _gio_mod

# Services / utils pulled in by the widgets
_img_cache = types.SimpleNamespace(get_or_fetch_cover_path=lambda url: None)
sys.modules["discogs_player.services.image_cache"] = _img_cache

_fmt = types.SimpleNamespace(format_market_summary=lambda item: "n/a")
sys.modules["discogs_player.ui.utils.formatting"] = _fmt

# ============================================================
# Synchronous GLib callback registry
# ============================================================

_callbacks: dict[int, object] = {}
_next_id = [1]


def _mock_timeout_add(interval, callback, *args):
    sid = _next_id[0]
    _next_id[0] += 1
    _callbacks[sid] = callback
    return sid


def _mock_source_remove(sid):
    _callbacks.pop(sid, None)


def _tick_all() -> None:
    """Fire every registered timeout callback once; remove those that return False."""
    for sid, cb in list(_callbacks.items()):
        if sid not in _callbacks:
            continue
        if not cb():
            _callbacks.pop(sid, None)


_glib_mod.timeout_add = _mock_timeout_add
_glib_mod.source_remove = _mock_source_remove

# ============================================================
# Widget imports — must follow sys.modules setup
# ============================================================

from discogs_player.ui.widgets.cover_carousel import CoverCarousel  # noqa: E402
from discogs_player.ui.widgets.spin_wheel import SpinWheel  # noqa: E402

# ============================================================
# Shared fixtures and helpers
# ============================================================


def _make_releases(n: int = 10) -> list[dict[str, object]]:
    return [
        {"discogs_release_id": i, "title": f"Release {i}", "cover_url": f"http://u{i}"}
        for i in range(n)
    ]


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset callback registry before and after each test."""
    _callbacks.clear()
    _next_id[0] = 1
    yield
    _callbacks.clear()


@pytest.fixture
def carousel():
    """CoverCarousel loaded with 10 items; executor is shut down after each test."""
    c = CoverCarousel()
    c.set_items(_make_releases(10))
    yield c
    c._prefetch_executor.shutdown(wait=False, cancel_futures=True)


@pytest.fixture
def wheel():
    return SpinWheel()


# ============================================================
# CoverCarousel animation tests
# ============================================================


def test_carousel_spin_starts_with_source_id(carousel):
    carousel.start_center_spin_animation()
    assert carousel._center_spin_source_id is not None


def test_carousel_spin_advances_index(carousel):
    carousel.start_center_spin_animation()
    initial = carousel._index
    _tick_all()
    _tick_all()
    assert carousel._index != initial


def test_carousel_spin_stops_at_target(carousel):
    carousel.start_center_spin_animation()
    carousel.set_spin_target_release(5)
    for _ in range(200):
        if carousel._center_spin_source_id is None:
            break
        _tick_all()
    assert carousel._center_spin_source_id is None
    assert carousel._index == 5


def test_carousel_spin_restart_after_completion(carousel):
    """Regression: second spin must start and sustain after the first completes."""
    # Spin 1
    carousel.start_center_spin_animation()
    carousel.set_spin_target_release(3)
    for _ in range(200):
        if carousel._center_spin_source_id is None:
            break
        _tick_all()
    assert carousel._center_spin_source_id is None, "Spin 1 did not finish"
    assert carousel._index == 3

    # Spin 2 — must start cleanly and sustain
    carousel.start_center_spin_animation()
    assert carousel._center_spin_source_id is not None, "Spin 2 did not start"
    for _ in range(5):
        _tick_all()
    assert carousel._center_spin_source_id is not None, "Spin 2 stopped prematurely"


def test_carousel_stop_clears_source_id(carousel):
    carousel.start_center_spin_animation()
    assert carousel._center_spin_source_id is not None
    carousel.stop_center_spin_animation()
    assert carousel._center_spin_source_id is None


def test_carousel_spin_skipped_for_single_item():
    """Single-item carousel must skip the animation (no source registered)."""
    c = CoverCarousel()
    c.set_items(_make_releases(1))
    c.start_center_spin_animation()
    assert c._center_spin_source_id is None
    c._prefetch_executor.shutdown(wait=False, cancel_futures=True)


# ============================================================
# SpinWheel animation tests
# ============================================================


def test_spin_wheel_starts_with_source_id(wheel):
    wheel.start_spin_animation()
    assert wheel._spin_source_id is not None


def test_spin_wheel_source_cleared_after_completion(wheel):
    wheel.start_spin_animation()
    payload = {
        "release": {"discogs_release_id": 1, "artist": "A", "title": "T", "year": 2000}
    }
    wheel.complete_spin_animation(payload)
    for _ in range(SpinWheel._SPIN_TICKS + 5):
        _tick_all()
    assert wheel._spin_source_id is None


def test_spin_wheel_restart_after_completion(wheel):
    """Regression: SpinWheel must accept a second spin after the first completes."""
    payload = {
        "release": {"discogs_release_id": 1, "artist": "A", "title": "T", "year": 2000}
    }
    # Spin 1
    wheel.start_spin_animation()
    wheel.complete_spin_animation(payload)
    for _ in range(SpinWheel._SPIN_TICKS + 10):
        _tick_all()
    assert wheel._spin_source_id is None, "Spin 1 source not cleared"

    # Spin 2
    wheel.start_spin_animation()
    assert wheel._spin_source_id is not None, "Spin 2 did not start"
    for _ in range(5):
        _tick_all()
    assert wheel._spin_source_id is not None, "Spin 2 stopped prematurely"


def test_spin_wheel_start_cancels_prior_animation(wheel):
    """Starting a new spin must cancel and deregister the previous one."""
    wheel.start_spin_animation()
    first_id = wheel._spin_source_id

    wheel.start_spin_animation()
    second_id = wheel._spin_source_id

    assert second_id is not None
    assert second_id != first_id
    assert first_id not in _callbacks, "Previous callback was not cancelled"
