"""Tests for scripts/headless_screenshot.py.

Static tests (always run, no GTK/Xvfb needed):
  - script exists and is executable
  - script is syntactically valid Python
  - CAPTURE_PLAN covers the expected four views
  - output directories are rooted under docs/media/

Integration test (skipped when Xvfb or optional deps are absent):
  - script runs to exit-code 0 and produces non-empty PNG files
"""

from __future__ import annotations

import ast
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "headless_screenshot.py"

EXPECTED_OUTPUT_FILENAMES = [
    "01-browse-gallery.png",
    "02-spin-result.png",
    "03-market-value-dashboard.png",
    "04-wantlist-view.png",
]


# ── helpers ────────────────────────────────────────────────────────────────────


def _ast_constants() -> dict:
    """Extract key module-level constants from the script via AST (no import)."""
    src = SCRIPT.read_text()
    tree = ast.parse(src)
    result: dict = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in (
                    "CAPTURE_PLAN",
                    "XVFB_DISPLAY",
                    "WIN_W",
                    "WIN_H",
                    "NAV_SETTLE_MS",
                    "INITIAL_DELAY_MS",
                    "STEP_GAP_MS",
                ):
                    try:
                        result[target.id] = ast.literal_eval(node.value)
                    except (ValueError, TypeError):
                        pass  # Path() expressions — skip
    return result


# ── static tests ───────────────────────────────────────────────────────────────


def test_headless_screenshot_script_exists():
    assert SCRIPT.exists(), f"Expected script not found: {SCRIPT}"


def test_headless_screenshot_script_is_executable():
    if not SCRIPT.exists():
        pytest.skip("script not present")
    assert os.access(SCRIPT, os.X_OK), "headless_screenshot.py is not executable"


def test_headless_screenshot_script_is_syntactically_valid():
    if not SCRIPT.exists():
        pytest.skip("script not present")
    # Parse without importing — the module mutates os.environ at import time.
    result = subprocess.run(
        [sys.executable, "-c",
         f"import ast, pathlib; ast.parse(pathlib.Path({str(SCRIPT)!r}).read_text()); print('ok')"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, f"Syntax check failed:\n{result.stderr}"
    assert result.stdout.strip() == "ok"


def test_headless_screenshot_capture_plan_covers_four_views():
    if not SCRIPT.exists():
        pytest.skip("script not present")
    constants = _ast_constants()
    plan = constants.get("CAPTURE_PLAN")
    assert plan is not None, "CAPTURE_PLAN not found in script"
    assert len(plan) == 4, f"Expected 4 capture steps, got {len(plan)}: {plan}"

    main_pages = {entry[0] for entry in plan}
    assert "browse" in main_pages, "CAPTURE_PLAN missing 'browse' view"
    assert "value" in main_pages, "CAPTURE_PLAN missing 'value' view"
    assert "wantlist" in main_pages, "CAPTURE_PLAN missing 'wantlist' view"


def test_headless_screenshot_capture_plan_output_filenames_match_expected():
    if not SCRIPT.exists():
        pytest.skip("script not present")
    constants = _ast_constants()
    plan = constants.get("CAPTURE_PLAN")
    assert plan is not None
    actual_filenames = [entry[2] for entry in plan]
    assert actual_filenames == EXPECTED_OUTPUT_FILENAMES, (
        f"Output filename list changed.\n"
        f"  expected: {EXPECTED_OUTPUT_FILENAMES}\n"
        f"  actual:   {actual_filenames}"
    )


def test_headless_screenshot_output_dirs_are_within_docs_media():
    """Confirm output paths are rooted under docs/media/ (not arbitrary temp dirs)."""
    if not SCRIPT.exists():
        pytest.skip("script not present")
    src = SCRIPT.read_text()
    tree = ast.parse(src)
    dir_paths: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in ("SCREENSHOTS_DIR", "GIF_DIR"):
                    dir_paths[target.id] = ast.unparse(node.value)
    assert "SCREENSHOTS_DIR" in dir_paths, "SCREENSHOTS_DIR not found"
    assert "GIF_DIR" in dir_paths, "GIF_DIR not found"
    assert "docs" in dir_paths["SCREENSHOTS_DIR"] and "media" in dir_paths["SCREENSHOTS_DIR"]
    assert "docs" in dir_paths["GIF_DIR"] and "media" in dir_paths["GIF_DIR"]


def test_headless_screenshot_timing_constants_are_sane():
    if not SCRIPT.exists():
        pytest.skip("script not present")
    c = _ast_constants()
    # NAV_SETTLE_MS: time allowed for GTK to repaint after navigation
    assert c.get("NAV_SETTLE_MS", 0) >= 500, "NAV_SETTLE_MS too short to reliably capture"
    assert c.get("NAV_SETTLE_MS", 999999) <= 5000, "NAV_SETTLE_MS unreasonably long"
    # INITIAL_DELAY_MS: wait after load_releases — must allow covers to load
    assert c.get("INITIAL_DELAY_MS", 0) >= 2000, "INITIAL_DELAY_MS too short"


# ── integration test ───────────────────────────────────────────────────────────


def _have_headless_deps() -> tuple[bool, str]:
    """Return (True, '') if all runtime deps are present, else (False, reason)."""
    if not SCRIPT.exists():
        return False, "headless_screenshot.py not present"
    if shutil.which("Xvfb") is None:
        return False, "Xvfb not installed"
    try:
        subprocess.run(
            [sys.executable, "-c", "import Xlib"],
            capture_output=True, check=True, timeout=5,
        )
    except subprocess.CalledProcessError:
        return False, "python-xlib not available"
    try:
        subprocess.run(
            [sys.executable, "-c", "from PIL import Image"],
            capture_output=True, check=True, timeout=5,
        )
    except subprocess.CalledProcessError:
        return False, "Pillow not available"
    return True, ""


def test_headless_screenshot_script_produces_output_files():
    ok, reason = _have_headless_deps()
    if not ok:
        pytest.skip(reason)

    completed = subprocess.run(
        [sys.executable, "scripts/headless_screenshot.py"],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        timeout=180,
        check=False,
    )

    if completed.returncode != 0:
        combined = (completed.stdout or "") + "\n" + (completed.stderr or "")
        if (
            "Gtk couldn't be initialized" in combined
            or "cannot open display" in combined.lower()
            or "Missing dependencies" in combined
        ):
            pytest.skip("GUI display runtime unavailable at execution time")
        pytest.fail(
            f"headless_screenshot.py exited {completed.returncode}:\n"
            f"stdout: {completed.stdout}\nstderr: {completed.stderr}"
        )

    stdout = completed.stdout or ""
    assert "=== Output ===" in stdout, (
        f"Expected '=== Output ===' in stdout, got:\n{stdout}"
    )

    screenshots_dir = ROOT / "docs" / "media" / "screenshots"
    for fname in EXPECTED_OUTPUT_FILENAMES:
        fpath = screenshots_dir / fname
        assert fpath.exists(), f"Expected screenshot not produced: {fpath}"
        assert fpath.stat().st_size > 0, f"Screenshot file is empty: {fpath}"
        assert fname in stdout, f"Filename '{fname}' not mentioned in script output"

    gif_path = ROOT / "docs" / "media" / "gif" / "product-demo.gif"
    assert gif_path.exists(), "product-demo.gif was not produced"
    assert gif_path.stat().st_size > 0, "product-demo.gif is empty"
