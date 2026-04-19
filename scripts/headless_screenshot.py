#!/usr/bin/env python3
"""headless_screenshot.py — Capture README screenshots from the live GTK4 app under Xvfb.

Runs entirely from a terminal with no desktop session required.

Usage (from repo root):
    python3 scripts/headless_screenshot.py

Requirements (automatically checked):
    - Xvfb          : sudo apt install xvfb   (already present on this machine)
    - python-xlib   : pip3 install --user python-xlib
    - Pillow        : already available on system Python
    - gi / GTK4     : python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 (system packages)

Output:
    docs/media/screenshots/01-browse-gallery.png
    docs/media/screenshots/02-spin-result.png
    docs/media/screenshots/03-market-value-dashboard.png
    docs/media/screenshots/04-wantlist-view.png
    docs/media/screenshots/05-setup-wizard.png
    docs/media/gif/product-demo.gif
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
SCREENSHOTS_DIR = ROOT / "docs" / "media" / "screenshots"
GIF_DIR = ROOT / "docs" / "media" / "gif"
XVFB_DISPLAY = ":99"
_DISPLAY_CANDIDATE_OFFSETS = tuple(range(0, 8))
WIN_W, WIN_H = 1440, 900
SYSTEM_DISPLAY = str(os.environ.get("DISPLAY") or "").strip()
ACTIVE_DISPLAY = XVFB_DISPLAY

# ── Environment (must happen before any gi / GTK import) ─────────────────────
os.environ.setdefault("GDK_BACKEND", "x11")
os.environ.setdefault("GSK_RENDERER", "cairo")
os.environ.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")
_xdg = f"/tmp/dplayer-headless-{os.getuid()}"
os.makedirs(_xdg, mode=0o700, exist_ok=True)
os.environ["XDG_RUNTIME_DIR"] = _xdg

# Make discogs_player importable from source tree (mirrors gui_smoke_test.sh)
sys.path.insert(0, str(ROOT / "src"))

# ── Screenshot capture plan ───────────────────────────────────────────────────
# (main_stack_name, sub_stack_name_or_None, output_filename, special_or_None)
CAPTURE_PLAN = [
    ("browse",   "gallery",  "01-browse-gallery.png",         None),
    ("browse",   "carousel", "02-spin-result.png",            None),
    ("value",    None,       "03-market-value-dashboard.png", None),
    ("wantlist", "gallery",  "04-wantlist-view.png",          None),
    ("browse",   "gallery",  "05-setup-wizard.png",           "open_wizard"),
]
# ms to wait after navigation before capturing
NAV_SETTLE_MS = 1200
# ms between capture steps
STEP_GAP_MS = 500
# ms after load_releases before starting sequence
INITIAL_DELAY_MS = 5000


# ── Xvfb ─────────────────────────────────────────────────────────────────────

def _display_name(base_display: str, offset: int) -> str:
    base_number = int(str(base_display).lstrip(":") or "99")
    return f":{base_number + int(offset)}"


def _set_active_display(display_name: str) -> None:
    global ACTIVE_DISPLAY
    ACTIVE_DISPLAY = display_name
    os.environ["DISPLAY"] = display_name


def start_xvfb() -> tuple[subprocess.Popen | None, str]:
    last_error = "unknown error"
    for offset in _DISPLAY_CANDIDATE_OFFSETS:
        display_name = _display_name(XVFB_DISPLAY, offset)
        print(f"Starting Xvfb on {display_name} ({WIN_W}x{WIN_H})...")
        proc = subprocess.Popen(
            ["Xvfb", display_name, "-screen", "0", f"{WIN_W}x{WIN_H}x24"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        time.sleep(1.5)
        if proc.poll() is None:
            _set_active_display(display_name)
            return proc, display_name

        stderr = ""
        if proc.stderr is not None:
            stderr = proc.stderr.read().strip()
        last_error = stderr or f"Xvfb exited with code {proc.returncode}"
        print(f"  Xvfb unavailable on {display_name}: {last_error}")

    if SYSTEM_DISPLAY:
        print(f"Falling back to existing display {SYSTEM_DISPLAY}")
        _set_active_display(SYSTEM_DISPLAY)
        return None, SYSTEM_DISPLAY

    raise RuntimeError(
        "Xvfb could not start on any candidate display. "
        f"Last error: {last_error}"
    )


# ── Screen capture ────────────────────────────────────────────────────────────

def capture_screen(path: Path) -> None:
    """Capture the full Xvfb display to a PNG using python-xlib + Pillow."""
    from Xlib import X  # type: ignore[import]
    from Xlib import display as xdisplay  # type: ignore[import]
    from PIL import Image

    d = xdisplay.Display(ACTIVE_DISPLAY)
    root = d.screen().root
    g = root.get_geometry()
    raw = root.get_image(0, 0, g.width, g.height, X.ZPixmap, 0xFFFFFFFF)
    d.close()

    # Xvfb on x86_64 uses BGRX byte ordering
    img = Image.frombytes("RGBX", (g.width, g.height), raw.data, "raw", "BGRX")
    img = img.convert("RGB")
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(path), optimize=True)
    kb = path.stat().st_size // 1024
    print(f"  [{path.name}]  {kb} KB")


# ── GIF assembly ──────────────────────────────────────────────────────────────

def assemble_gif(frames: list[Path]) -> None:
    from PIL import Image

    if not frames:
        print("WARN: no frames to assemble into GIF")
        return

    output = GIF_DIR / "product-demo.gif"
    GIF_DIR.mkdir(parents=True, exist_ok=True)

    imgs = [Image.open(str(f)).convert("P", palette=Image.ADAPTIVE, colors=256) for f in frames]
    imgs[0].save(
        str(output),
        save_all=True,
        append_images=imgs[1:],
        duration=3000,
        loop=0,
        optimize=True,
    )
    kb = output.stat().st_size // 1024
    print(f"  [product-demo.gif]  {kb} KB")


# ── Navigation + capture sequencer ───────────────────────────────────────────

class _Sequencer:
    """Drives GTK navigation and screenshot capture via GLib timeout callbacks."""

    def __init__(self, window, GLib, app):  # type: ignore[type-arg]
        self._w = window
        self._GLib = GLib
        self._app = app
        self._step = 0
        self._pending: Path | None = None
        self._frames: list[Path] = []

    def start(self) -> None:
        print(f"\nStarting screenshot sequence ({len(CAPTURE_PLAN)} views)...")
        self._GLib.timeout_add(INITIAL_DELAY_MS, self._run_step)

    def _run_step(self) -> bool:
        if self._step >= len(CAPTURE_PLAN):
            self._GLib.timeout_add(300, self._finish)
            return False

        main_page, sub_page, filename, special = CAPTURE_PLAN[self._step]
        self._step += 1
        self._pending = SCREENSHOTS_DIR / filename

        print(f"\n  → {main_page}/{sub_page or '-'}  →  {filename}")

        w = self._w
        # Navigate main tab
        if hasattr(w, "_main_stack"):
            w._main_stack.set_visible_child_name(main_page)

        # Navigate sub-stack
        if sub_page is not None:
            if main_page == "browse" and hasattr(w, "_browse_stack"):
                w._browse_stack.set_visible_child_name(sub_page)
            elif main_page == "wantlist" and hasattr(w, "_wantlist_stack"):
                w._wantlist_stack.set_visible_child_name(sub_page)

        if special == "open_wizard":
            w._open_setup_wizard()

        self._GLib.timeout_add(NAV_SETTLE_MS, self._capture)
        return False

    def _capture(self) -> bool:
        assert self._pending is not None
        capture_screen(self._pending)
        self._frames.append(self._pending)
        self._GLib.timeout_add(STEP_GAP_MS, self._run_step)
        return False

    def _finish(self) -> bool:
        print("\nAssembling GIF...")
        assemble_gif(self._frames)
        self._app.quit()
        return False


# ── Headless app subclass ─────────────────────────────────────────────────────

def _build_app():  # type: ignore[return]
    """Import GTK4 and return a configured HeadlessScreenshotApp instance."""
    try:
        import gi  # type: ignore[import]
    except ModuleNotFoundError:
        sys.exit(
            "ERROR: python3-gi not found.\n"
            "Install: sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1"
        )

    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    from gi.repository import GLib  # type: ignore[import]

    from discogs_player.ui.main_window import DiscogsPlayerApp, MainWindow  # type: ignore[import]

    class HeadlessScreenshotApp(DiscogsPlayerApp):
        """DiscogsPlayerApp subclass that captures screenshots then exits."""

        def do_activate(self) -> None:  # type: ignore[override]
            if self._did_activate:
                return
            self._did_activate = True

            import traceback as _tb

            try:
                # Build window with local data only (no cover preloading)
                window = MainWindow(self, limit=self._limit, preload_covers=self._preload_covers)
                window.present()
                # Synchronous load — same path as --smoke-test, populates all views
                window.load_releases(background=False)
            except Exception as exc:
                print(f"ERROR: {exc}", file=sys.stderr)
                print(_tb.format_exc(), file=sys.stderr)
                self.quit()
                return

            seq = _Sequencer(window, GLib, self)
            seq.start()

    return HeadlessScreenshotApp(limit=30, preload_covers=True)


# ── Dependency check ──────────────────────────────────────────────────────────

def _check_deps() -> None:
    missing = []
    if not Path("/usr/bin/Xvfb").exists() and not Path("/usr/bin/Xvfb").exists():
        missing.append("xvfb  (sudo apt install xvfb)")
    try:
        import Xlib  # type: ignore[import]  # noqa: F401
    except ModuleNotFoundError:
        missing.append("python-xlib  (pip3 install --user --break-system-packages python-xlib)")
    try:
        from PIL import Image  # type: ignore[import]  # noqa: F401
    except ModuleNotFoundError:
        missing.append("Pillow  (pip3 install --user --break-system-packages Pillow)")
    if missing:
        print("Missing dependencies:")
        for m in missing:
            print(f"  {m}")
        sys.exit(1)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    _check_deps()

    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    GIF_DIR.mkdir(parents=True, exist_ok=True)

    xvfb, display_name = start_xvfb()
    rc = 1
    try:
        print(f"Using Xvfb display {display_name}")
        app = _build_app()
        print("Running GTK4 app headlessly...")
        app.run(["headless-screenshot"])
        rc = getattr(app, "exit_code", 0)
    except Exception as exc:
        import traceback
        print(f"FATAL: {exc}", file=sys.stderr)
        traceback.print_exc()
    finally:
        print("\nStopping Xvfb...")
        if xvfb is not None:
            xvfb.terminate()
            try:
                xvfb.wait(timeout=5)
            except subprocess.TimeoutExpired:
                xvfb.kill()

    print("\n=== Output ===")
    for f in sorted(SCREENSHOTS_DIR.glob("0*.png")):
        kb = f.stat().st_size // 1024
        print(f"  {kb:>4} KB  {f.name}")
    gif = GIF_DIR / "product-demo.gif"
    if gif.exists():
        kb = gif.stat().st_size // 1024
        print(f"  {kb:>4} KB  product-demo.gif")

    return rc


if __name__ == "__main__":
    raise SystemExit(main())
