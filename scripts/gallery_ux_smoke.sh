#!/usr/bin/env bash
set -euo pipefail

if ! command -v xvfb-run >/dev/null 2>&1; then
  echo "Missing dependency: xvfb-run" >&2
  echo "Install on Pop!_OS: sudo apt update && sudo apt install -y xvfb" >&2
  exit 1
fi

LIMIT="${1:-12}"

# Improve stability in headless CI/SSH sessions.
export GSK_RENDERER="${GSK_RENDERER:-cairo}"
export LIBGL_ALWAYS_SOFTWARE="${LIBGL_ALWAYS_SOFTWARE:-1}"
export XDG_RUNTIME_DIR="/tmp/dplayer-runtime-$UID"
mkdir -p "${XDG_RUNTIME_DIR}"
chmod 700 "${XDG_RUNTIME_DIR}"
export DP_GALLERY_UX_LIMIT="${LIMIT}"

if [ -f ".venv/bin/python" ]; then
  # Prefer venv Python when it can import gi, otherwise fall back to system Python.
  if .venv/bin/python - <<'PY' >/dev/null 2>&1
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")
print("ok")
PY
  then
    PYTHON_BIN=".venv/bin/python"
  fi
fi

if [ -z "${PYTHON_BIN:-}" ]; then
  if [ -x "/usr/bin/python3" ]; then
    PYTHON_BIN="/usr/bin/python3"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
  else
    echo "Missing dependency: python3" >&2
    exit 1
  fi
fi

PYTHONPATH=src xvfb-run -a "${PYTHON_BIN}" - <<'PY'
from __future__ import annotations

import json
import os
import time
import traceback

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")
from gi.repository import Adw, Gdk, GLib

from discogs_player.ui.main_window import MainWindow


def _to_positive_int(value: str, *, default: int = 12) -> int:
    try:
        parsed = int(str(value).strip())
    except Exception:
        return default
    if parsed <= 0:
        return default
    return parsed


def _next_with_wrap(base: int, delta: int, count: int, offset_start: int) -> int:
    return offset_start + (((base - offset_start) + delta) % count)


def _detail_width(scroller) -> int:
    get_min_content_width = getattr(scroller, "get_min_content_width", None)
    if callable(get_min_content_width):
        try:
            return max(0, int(get_min_content_width() or 0))
        except Exception:
            pass
    return max(0, int(scroller.get_width() or 0))


def _browse_carousel_metrics(window) -> dict[str, int]:
    panel_height = int(window._browse_panel.get_height() or 0)
    stack_width = int(window._browse_stack.get_width() or 0)
    stack_height = int(window._browse_stack.get_height() or 0)
    return {
        "detail_width": _detail_width(window._sidebar_scroll),
        "stack_width": stack_width,
        "stack_height": stack_height,
        "top_chrome_height": max(0, panel_height - stack_height),
        "center_slot_width": int(window._carousel._center_slot_width or 0),
        "center_slot_height": int(window._carousel._center_slot_height or 0),
    }


def _assert_metric_close(
    *,
    section: str,
    stage: str,
    name: str,
    observed: int,
    expected: int,
    tolerance: int,
) -> None:
    assert abs(int(observed) - int(expected)) <= int(tolerance), {
        "section": section,
        "stage": stage,
        "metric": name,
        "observed": int(observed),
        "expected": int(expected),
        "tolerance": int(tolerance),
    }


def _maximize_or_expand(window, *, base_width: int, base_height: int) -> tuple[int, int]:
    window.maximize()
    GalleryUxSmokeApp._pump(0.35)
    width = int(window.get_width() or 0)
    height = int(window.get_height() or 0)
    if width > base_width and height > base_height:
        return width, height

    target_width = max(base_width + 360, 1480)
    target_height = max(base_height + 220, 920)
    window.set_default_size(target_width, target_height)
    window.queue_resize()
    GalleryUxSmokeApp._pump(0.45)
    return int(window.get_width() or 0), int(window.get_height() or 0)


class GalleryUxSmokeApp(Adw.Application):
    def __init__(self, *, limit: int) -> None:
        super().__init__(application_id="com.discogs_player.gallery.ux.smoke")
        self._limit = max(12, int(limit))
        self._window: MainWindow | None = None
        self.result: dict[str, object] = {"ok": False}

    @staticmethod
    def _pump(seconds: float = 0.0) -> None:
        ctx = GLib.MainContext.default()
        end = time.monotonic() + max(0.0, float(seconds))
        while time.monotonic() < end:
            while ctx.pending():
                ctx.iteration(False)
            time.sleep(0.01)
        while ctx.pending():
            ctx.iteration(False)

    def do_activate(self) -> None:
        if self._window is not None:
            self._window.present()
            return
        self._window = MainWindow(self, limit=self._limit, preload_covers=False)
        self._window.present()
        GLib.timeout_add(220, self._run_checks)

    def _run_checks(self) -> bool:
        assert self._window is not None
        window = self._window
        try:
            self._pump(0.25)
            startup_width = int(window.get_width() or 0)
            startup_height = int(window.get_height() or 0)

            browse_items = [
                {
                    "discogs_release_id": 3000 + i,
                    "title": f"Browse {i}",
                    "artist": "Artist",
                    "year": 2000 + i,
                    "cover_path": "",
                }
                for i in range(max(self._limit, 36))
            ]
            wantlist_items = [
                {
                    "discogs_release_id": 4000 + i,
                    "title": f"Wantlist {i}",
                    "artist": "Artist",
                    "year": 1990 + i,
                    "cover_path": "",
                }
                for i in range(max(self._limit, 36))
            ]

            window._apply_release_load_result(
                {"items": browse_items, "cover_cached_count": 0},
                preferred_release_id=None,
            )
            window._apply_wantlist_load_result(
                {"items": wantlist_items, "cover_cached_count": 0},
                preferred_release_id=None,
            )
            self._pump(0.45)
            startup_browse_carousel = _browse_carousel_metrics(window)

            window._main_stack.set_visible_child_name("value")
            self._pump(0.18)
            window._main_stack.set_visible_child_name("browse")
            self._pump(0.45)
            startup_browse_carousel_repaired = _browse_carousel_metrics(window)

            for metric_name, tolerance in (
                ("detail_width", 28),
                ("top_chrome_height", 28),
                ("center_slot_width", 48),
                ("center_slot_height", 48),
            ):
                _assert_metric_close(
                    section="browse",
                    stage="startup",
                    name=metric_name,
                    observed=startup_browse_carousel[metric_name],
                    expected=startup_browse_carousel_repaired[metric_name],
                    tolerance=tolerance,
                )

            maximized_width, maximized_height = _maximize_or_expand(
                window,
                base_width=startup_width,
                base_height=startup_height,
            )
            self._pump(0.45)
            maximized_browse_carousel = _browse_carousel_metrics(window)

            window._main_stack.set_visible_child_name("queue")
            self._pump(0.18)
            window._main_stack.set_visible_child_name("browse")
            self._pump(0.45)
            maximized_browse_carousel_repaired = _browse_carousel_metrics(window)

            for metric_name, tolerance in (
                ("detail_width", 28),
                ("top_chrome_height", 28),
                ("center_slot_width", 48),
                ("center_slot_height", 48),
            ):
                _assert_metric_close(
                    section="browse",
                    stage="maximized",
                    name=metric_name,
                    observed=maximized_browse_carousel[metric_name],
                    expected=maximized_browse_carousel_repaired[metric_name],
                    tolerance=tolerance,
                )

            browse_carousel_detail_width = startup_browse_carousel["detail_width"]

            # Browse status consistency via toggle buttons.
            window._gallery_mode.set_active(True)
            self._pump(0.12)
            browse_gallery_status = window._status.get_text()
            assert browse_gallery_status == "Browse mode: Gallery"
            browse_overflow_expected = (
                len(browse_items) > (window._browse_gallery.current_columns() * 3)
            )
            assert browse_overflow_expected is True, {
                "section": "browse",
                "reason": "gallery dataset does not exceed the visible three-row target",
                "columns": window._browse_gallery.current_columns(),
                "item_count": len(browse_items),
            }

            window._text_mode.set_active(True)
            self._pump(0.12)
            browse_text_status = window._status.get_text()
            assert browse_text_status == "Browse mode: Text Menu"

            window._carousel_mode.set_active(True)
            self._pump(0.12)
            browse_carousel_status = window._status.get_text()
            assert browse_carousel_status == "Browse mode: Carousel"

            # Browse gallery keyboard stepping.
            window._gallery_mode.set_active(True)
            self._pump(0.12)
            window._gallery_mode.grab_focus()
            self._pump(0.05)
            assert (
                window._handle_key_pressed(
                    None, Gdk.KEY_Down, 0, Gdk.ModifierType(0)
                )
                is True
            )
            self._pump(0.12)
            browse_first = int(window._selected_release_id or 0)
            assert browse_first == 3000
            browse_detail_release_id = int(window._album_detail._current_release_id or 0)
            assert browse_detail_release_id == browse_first, {
                "section": "browse",
                "reason": "detail pane did not follow first gallery selection",
                "selected": browse_first,
                "detail": browse_detail_release_id,
            }
            browse_detail_width_after_select = _detail_width(window._sidebar_scroll)
            assert browse_detail_width_after_select > 0, {
                "section": "browse",
                "reason": "detail pane stayed collapsed after gallery selection",
                "detail_width": browse_detail_width_after_select,
            }
            browse_clear_visible = bool(window._browse_gallery_clear_button.get_visible())
            assert browse_clear_visible is True, {
                "section": "browse",
                "reason": "clear-selection button hidden after gallery selection",
            }

            assert (
                window._handle_key_pressed(
                    None, Gdk.KEY_Right, 0, Gdk.ModifierType(0)
                )
                is True
            )
            self._pump(0.12)
            browse_second = int(window._selected_release_id or 0)
            assert browse_second == 3001

            browse_columns_for_step = max(1, int(window._browse_gallery.current_columns()))
            assert (
                window._handle_key_pressed(
                    None, Gdk.KEY_Down, 0, Gdk.ModifierType(0)
                )
                is True
            )
            self._pump(0.12)
            browse_third = int(window._selected_release_id or 0)
            assert browse_third == _next_with_wrap(
                3001, browse_columns_for_step, self._limit, 3000
            )

            window._browse_gallery_clear_button.emit("clicked")
            self._pump(0.18)
            browse_clear_status = window._status.get_text()
            assert browse_clear_status == "Browse gallery selection cleared."
            browse_detail_width_after_clear = _detail_width(window._sidebar_scroll)
            assert browse_detail_width_after_clear == 0, {
                "section": "browse",
                "reason": "detail pane stayed open after clear",
                "detail_width": browse_detail_width_after_clear,
            }
            assert not bool(window._browse_gallery_clear_button.get_visible()), {
                "section": "browse",
                "reason": "clear-selection button still visible after clear",
            }

            # Wantlist status consistency via toggle buttons.
            window._main_stack.set_visible_child_name("wantlist")
            self._pump(0.12)
            want_carousel_detail_width = _detail_width(window._wantlist_sidebar_scroll)
            window._wantlist_gallery_mode.set_active(True)
            self._pump(0.12)
            want_gallery_status = window._status.get_text()
            assert want_gallery_status == "Wantlist mode: Gallery"
            want_overflow_expected = (
                len(wantlist_items) > (window._wantlist_gallery.current_columns() * 3)
            )
            assert want_overflow_expected is True, {
                "section": "wantlist",
                "reason": "gallery dataset does not exceed the visible three-row target",
                "columns": window._wantlist_gallery.current_columns(),
                "item_count": len(wantlist_items),
            }

            window._wantlist_text_mode.set_active(True)
            self._pump(0.12)
            want_text_status = window._status.get_text()
            assert want_text_status == "Wantlist mode: Text Menu"

            window._wantlist_carousel_mode.set_active(True)
            self._pump(0.12)
            want_carousel_status = window._status.get_text()
            assert want_carousel_status == "Wantlist mode: Carousel"

            # Wantlist gallery keyboard stepping.
            window._wantlist_gallery_mode.set_active(True)
            self._pump(0.12)
            window._wantlist_gallery_mode.grab_focus()
            self._pump(0.05)
            assert (
                window._handle_key_pressed(
                    None, Gdk.KEY_Down, 0, Gdk.ModifierType(0)
                )
                is True
            )
            self._pump(0.12)
            want_first = int(window._selected_wantlist_id or 0)
            assert want_first == 4000
            want_detail_release_id = int(
                window._wantlist_detail._current_release_id or 0
            )
            assert want_detail_release_id == want_first, {
                "section": "wantlist",
                "reason": "detail pane did not follow first gallery selection",
                "selected": want_first,
                "detail": want_detail_release_id,
            }
            want_detail_width_after_select = _detail_width(
                window._wantlist_sidebar_scroll
            )
            assert want_detail_width_after_select > 0, {
                "section": "wantlist",
                "reason": "detail pane stayed collapsed after gallery selection",
                "detail_width": want_detail_width_after_select,
            }
            want_clear_visible = bool(window._wantlist_gallery_clear_button.get_visible())
            assert want_clear_visible is True, {
                "section": "wantlist",
                "reason": "clear-selection button hidden after gallery selection",
            }

            assert (
                window._handle_key_pressed(
                    None, Gdk.KEY_Right, 0, Gdk.ModifierType(0)
                )
                is True
            )
            self._pump(0.12)
            want_second = int(window._selected_wantlist_id or 0)
            assert want_second == 4001

            want_columns_for_step = max(
                1, int(window._wantlist_gallery.current_columns())
            )
            assert (
                window._handle_key_pressed(
                    None, Gdk.KEY_Down, 0, Gdk.ModifierType(0)
                )
                is True
            )
            self._pump(0.12)
            want_third = int(window._selected_wantlist_id or 0)
            assert want_third == _next_with_wrap(
                4001, want_columns_for_step, self._limit, 4000
            )

            window._wantlist_gallery_clear_button.emit("clicked")
            self._pump(0.18)
            want_clear_status = window._status.get_text()
            assert want_clear_status == "Wantlist gallery selection cleared."
            want_detail_width_after_clear = _detail_width(
                window._wantlist_sidebar_scroll
            )
            assert want_detail_width_after_clear == 0, {
                "section": "wantlist",
                "reason": "detail pane stayed open after clear",
                "detail_width": want_detail_width_after_clear,
            }
            assert not bool(window._wantlist_gallery_clear_button.get_visible()), {
                "section": "wantlist",
                "reason": "clear-selection button still visible after clear",
            }

            self.result = {
                "ok": True,
                "limit": self._limit,
                "startup": {
                    "width": startup_width,
                    "height": startup_height,
                    "browse_carousel_detail_width": browse_carousel_detail_width,
                    "browse_carousel": startup_browse_carousel,
                    "browse_carousel_repaired": startup_browse_carousel_repaired,
                    "wantlist_carousel_detail_width": want_carousel_detail_width,
                },
                "maximized": {
                    "width": maximized_width,
                    "height": maximized_height,
                    "browse_carousel": maximized_browse_carousel,
                    "browse_carousel_repaired": maximized_browse_carousel_repaired,
                },
                "browse": {
                    "columns_for_down_step": browse_columns_for_step,
                    "overflow_expected": browse_overflow_expected,
                    "detail_release_id": browse_detail_release_id,
                    "detail_width_after_select": browse_detail_width_after_select,
                    "detail_width_after_clear": browse_detail_width_after_clear,
                    "statuses": [
                        browse_gallery_status,
                        browse_text_status,
                        browse_carousel_status,
                        browse_clear_status,
                    ],
                    "ids": [browse_first, browse_second, browse_third],
                },
                "wantlist": {
                    "columns_for_down_step": want_columns_for_step,
                    "overflow_expected": want_overflow_expected,
                    "detail_release_id": want_detail_release_id,
                    "detail_width_after_select": want_detail_width_after_select,
                    "detail_width_after_clear": want_detail_width_after_clear,
                    "statuses": [
                        want_gallery_status,
                        want_text_status,
                        want_carousel_status,
                        want_clear_status,
                    ],
                    "ids": [want_first, want_second, want_third],
                },
            }
        except Exception as exc:
            self.result = {
                "ok": False,
                "error": str(exc),
                "traceback": traceback.format_exc(limit=12),
            }
        finally:
            if self._window is not None:
                self._window.close()
            self.quit()
        return False


limit = _to_positive_int(os.getenv("DP_GALLERY_UX_LIMIT", "12"), default=12)
app = GalleryUxSmokeApp(limit=limit)
app.run([])
print(json.dumps(app.result, sort_keys=True))
if not bool(app.result.get("ok")):
    raise SystemExit(1)
PY
