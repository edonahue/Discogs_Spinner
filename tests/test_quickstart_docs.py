from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def test_quickstart_docs_exist_and_include_core_onboarding_steps():
    docs = {
        "docs/quickstart_windows.md": (
            "dplayer setup",
            "dplayer sync",
            "dplayer status",
            "dplayer auth spotify-doctor",
        ),
        "docs/quickstart_debian.md": (
            "dplayer setup",
            "dplayer sync",
            "dplayer status",
            "pip install -e \".[spotify]\"",
        ),
        "docs/quickstart_macos.md": (
            "dplayer setup",
            "dplayer sync",
            "dplayer status",
            "pip install -e \".[spotify]\"",
        ),
    }

    for rel_path, markers in docs.items():
        source = _read(rel_path)
        for marker in markers:
            assert marker in source


def test_readme_links_os_quickstarts():
    source = _read("README.md")
    for marker in (
        "## OS Quickstarts",
        "docs/quickstart_windows.md",
        "docs/quickstart_debian.md",
        "docs/quickstart_macos.md",
    ):
        assert marker in source
