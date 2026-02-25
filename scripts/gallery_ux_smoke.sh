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

            browse_items = [
                {
                    "discogs_release_id": 3000 + i,
                    "title": f"Browse {i}",
                    "artist": "Artist",
                    "year": 2000 + i,
                    "cover_path": "",
                }
                for i in range(self._limit)
            ]
            wantlist_items = [
                {
                    "discogs_release_id": 4000 + i,
                    "title": f"Wantlist {i}",
                    "artist": "Artist",
                    "year": 1990 + i,
                    "cover_path": "",
                }
                for i in range(self._limit)
            ]

            window._apply_release_load_result(
                {"items": browse_items, "cover_cached_count": 0},
                preferred_release_id=None,
            )
            window._apply_wantlist_load_result(
                {"items": wantlist_items, "cover_cached_count": 0},
                preferred_release_id=None,
            )
            self._pump(0.25)

            # Browse status consistency via toggle buttons.
            window._gallery_mode.set_active(True)
            self._pump(0.12)
            browse_gallery_status = window._status.get_text()
            assert browse_gallery_status == "Browse mode: Gallery"

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

            window._browse_gallery._back_button.emit("clicked")
            self._pump(0.18)
            browse_back_status = window._status.get_text()
            assert browse_back_status == "Browse gallery selection cleared."

            # Wantlist status consistency via toggle buttons.
            window._main_stack.set_visible_child_name("wantlist")
            self._pump(0.12)
            window._wantlist_gallery_mode.set_active(True)
            self._pump(0.12)
            want_gallery_status = window._status.get_text()
            assert want_gallery_status == "Wantlist mode: Gallery"

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

            window._wantlist_gallery._back_button.emit("clicked")
            self._pump(0.18)
            want_back_status = window._status.get_text()
            assert want_back_status == "Wantlist gallery selection cleared."

            self.result = {
                "ok": True,
                "limit": self._limit,
                "browse": {
                    "columns_for_down_step": browse_columns_for_step,
                    "statuses": [
                        browse_gallery_status,
                        browse_text_status,
                        browse_carousel_status,
                        browse_back_status,
                    ],
                    "ids": [browse_first, browse_second, browse_third],
                },
                "wantlist": {
                    "columns_for_down_step": want_columns_for_step,
                    "statuses": [
                        want_gallery_status,
                        want_text_status,
                        want_carousel_status,
                        want_back_status,
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
