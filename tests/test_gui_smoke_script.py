from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def test_gui_smoke_script_emits_valid_json_when_gui_runtime_is_available():
    script_path = ROOT / "scripts" / "gui_smoke_test.sh"
    if not script_path.exists():
        pytest.skip("gui_smoke_test.sh not present")
    if shutil.which("xvfb-run") is None:
        pytest.skip("xvfb-run is not installed")

    completed = subprocess.run(
        ["bash", "-lc", "./scripts/gui_smoke_test.sh 6"],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )

    if completed.returncode != 0:
        stderr = (completed.stderr or "") + "\n" + (completed.stdout or "")
        if (
            "Missing GUI dependency:" in stderr
            or "Missing dependency: xvfb-run" in stderr
            or "Gtk couldn't be initialized" in stderr
        ):
            pytest.skip("GUI runtime dependencies unavailable for smoke execution")
        pytest.fail(f"gui smoke script failed: rc={completed.returncode}\n{stderr}")

    lines = [
        line.strip() for line in (completed.stdout or "").splitlines() if line.strip()
    ]
    assert lines, "gui smoke script produced no stdout"
    payload = json.loads(lines[-1])
    assert payload.get("ok") is True
    assert payload.get("titlebar_present") is True
    assert "item_count" in payload
    assert "sort" in payload
