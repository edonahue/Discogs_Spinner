from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def test_gallery_ux_smoke_script_emits_valid_json_when_gui_runtime_is_available():
    script_path = ROOT / "scripts" / "gallery_ux_smoke.sh"
    if not script_path.exists():
        pytest.skip("gallery_ux_smoke.sh not present")
    if shutil.which("xvfb-run") is None:
        pytest.skip("xvfb-run is not installed")

    completed = subprocess.run(
        ["bash", "-lc", "./scripts/gallery_ux_smoke.sh 12"],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        timeout=240,
        check=False,
    )

    if completed.returncode != 0:
        stderr = (completed.stderr or "") + "\n" + (completed.stdout or "")
        if (
            "Missing dependency: xvfb-run" in stderr
            or "Missing GUI dependency:" in stderr
            or "Gtk couldn't be initialized" in stderr
        ):
            pytest.skip("GUI runtime dependencies unavailable for smoke execution")
        pytest.fail(
            "gallery UX smoke script failed: "
            f"rc={completed.returncode}\n{stderr}"
        )

    lines = [
        line.strip() for line in (completed.stdout or "").splitlines() if line.strip()
    ]
    assert lines, "gallery UX smoke script produced no stdout"
    payload = json.loads(lines[-1])
    assert payload.get("ok") is True
    assert payload.get("limit") == 12

    startup = payload.get("startup")
    maximized = payload.get("maximized")
    browse = payload.get("browse")
    wantlist = payload.get("wantlist")
    assert isinstance(startup, dict)
    assert isinstance(maximized, dict)
    assert isinstance(browse, dict)
    assert isinstance(wantlist, dict)

    assert 0 < int(startup.get("target_width") or 0) <= 2400
    assert 0 < int(startup.get("target_height") or 0) <= 1100
    assert int(startup.get("width") or 0) > 0
    assert int(startup.get("height") or 0) > 0
    assert 0 < int(startup.get("browse_carousel_detail_width") or 0) <= 360
    assert 0 < int(startup.get("wantlist_carousel_detail_width") or 0) <= 300

    browse_statuses = browse.get("statuses")
    want_statuses = wantlist.get("statuses")
    assert isinstance(browse_statuses, list)
    assert isinstance(want_statuses, list)
    assert "Browse mode: Gallery" in browse_statuses
    assert "Browse gallery selection cleared." in browse_statuses
    assert "Wantlist mode: Gallery" in want_statuses
    assert "Wantlist gallery selection cleared." in want_statuses

    browse_ids = browse.get("ids")
    want_ids = wantlist.get("ids")
    assert isinstance(browse_ids, list)
    assert isinstance(want_ids, list)
    assert len(browse_ids) == 3
    assert len(want_ids) == 3
    assert browse.get("overflow_expected") is True
    assert wantlist.get("overflow_expected") is True
    assert browse.get("detail_release_id") == browse_ids[0]
    assert wantlist.get("detail_release_id") == want_ids[0]
    assert int(browse.get("detail_width_after_select") or 0) > 0
    assert int(wantlist.get("detail_width_after_select") or 0) > 0
    assert int(browse.get("detail_width_after_clear", -1)) == 0
    assert int(wantlist.get("detail_width_after_clear", -1)) == 0

    assert int(maximized.get("width") or 0) >= int(startup.get("width") or 0)
    assert int(maximized.get("height") or 0) > 0

    startup_browse = startup.get("browse_carousel")
    startup_browse_repaired = startup.get("browse_carousel_repaired")
    maximized_browse = maximized.get("browse_carousel")
    maximized_browse_repaired = maximized.get("browse_carousel_repaired")
    assert isinstance(startup_browse, dict)
    assert isinstance(startup_browse_repaired, dict)
    assert isinstance(maximized_browse, dict)
    assert isinstance(maximized_browse_repaired, dict)

    for key, tolerance in (
        ("detail_width", 28),
        ("top_chrome_height", 28),
        ("center_slot_width", 48),
        ("center_slot_height", 48),
    ):
        assert abs(
            int(startup_browse.get(key) or 0)
            - int(startup_browse_repaired.get(key) or 0)
        ) <= tolerance
        assert abs(
            int(maximized_browse.get(key) or 0)
            - int(maximized_browse_repaired.get(key) or 0)
        ) <= tolerance
