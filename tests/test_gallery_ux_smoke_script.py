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

    browse = payload.get("browse")
    wantlist = payload.get("wantlist")
    assert isinstance(browse, dict)
    assert isinstance(wantlist, dict)

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
