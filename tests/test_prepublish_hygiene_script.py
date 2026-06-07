from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _script_text(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def test_prepublish_hygiene_script_checks_expected_markers():
    source = _script_text("scripts/prepublish_hygiene_check.sh")
    for marker in (
        "git ls-files",
        ".env",
        "*.db",
        "exports/",
        "*.log",
        "LICENSE",
        "PRIVACY.md",
        "TERMS.md",
        "TRADEMARKS.md",
        "COMPLIANCE.md",
        "RELEASE_CHECKLIST_WINDOWS_DEBIAN_MACOS.md",
        "STRATEGIC_EXPANSION_NOTES_2026-02-26.md",
        "validate_linux_packaging_metadata.py",
        "io.github.edonahue.DiscogsSpinner.metainfo.xml",
        "prepublish hygiene: PASS",
    ):
        assert marker in source


def test_prepublish_hygiene_script_passes_in_current_repo():
    completed = subprocess.run(
        ["bash", "scripts/prepublish_hygiene_check.sh"],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "prepublish hygiene: PASS" in (completed.stdout + completed.stderr)
