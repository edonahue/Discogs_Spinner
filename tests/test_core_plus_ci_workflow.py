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
        "pip install \".[dev]\"",
        "pip install \".[dev,spotify]\"",
        "build-artifacts:",
        "ubuntu-latest",
        "macos-latest",
        "windows-latest",
        "./scripts/build_artifacts.sh all",
        "discogs_player-core-${{ matrix.os }}",
        "discogs_player-plus-${{ matrix.os }}",
    ):
        assert marker in source


# ---------------------------------------------------------------------------
# pyproject.toml version drift guard (added 2026-02-27)
# ---------------------------------------------------------------------------

def test_pyproject_version_not_default_placeholder():
    """pyproject.toml version must not be the initial placeholder '0.1.0'.

    The installed package version reported by `dplayer diagnostics` comes from
    importlib.metadata, which reads pyproject.toml. If this stays at '0.1.0'
    while git tags advance, diagnostics will report the wrong version.
    """
    import re
    pyproject = (Path(__file__).parents[1] / "pyproject.toml").read_text()
    match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
    assert match, "Could not find version field in pyproject.toml"
    version = match.group(1)
    assert version != "0.1.0", (
        "pyproject.toml version is still '0.1.0'. "
        "Update it to match the current release tag."
    )
    # Must look like a semver or PEP 440 version (e.g. 0.2.0rc5, 1.0.0, 0.2.0)
    assert re.match(r'^\d+\.\d+\.\d+', version), (
        f"pyproject.toml version '{version}' doesn't look like a valid version."
    )
