from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _workflow_text(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def test_core_plus_ci_workflow_has_split_profiles_and_os_artifacts():
    source = _workflow_text(".github/workflows/core_plus_ci.yml")
    for marker in (
        "prepublish-hygiene:",
        "scripts/prepublish_hygiene_check.sh",
        "test-core:",
        "test-plus:",
        "pip install .",
        "pip install \".[spotify]\"",
        "build-artifacts:",
        "ubuntu-latest",
        "macos-latest",
        "windows-latest",
        "./scripts/build_artifacts.sh all",
        "discogs_player-core-${{ matrix.os }}",
        "discogs_player-plus-${{ matrix.os }}",
    ):
        assert marker in source
