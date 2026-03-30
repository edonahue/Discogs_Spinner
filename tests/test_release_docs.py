from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def test_public_release_runbook_contains_installer_release_steps():
    source = _read("docs/PUBLIC_RELEASE_RUNBOOK.md")
    for marker in (
        "Installer Build",
        ".github/workflows/installer_build.yml",
        "git tag -a v0.2.0",
        "git push origin v0.2.0",
        "CHECKSUMS-INSTALLERS.txt",
        "RELEASE_NOTES_TEMPLATE.md",
    ):
        assert marker in source


def test_release_notes_template_references_quickstarts_and_diagnostics():
    source = _read("docs/RELEASE_NOTES_TEMPLATE.md")
    for marker in (
        "docs/quickstart_windows.md",
        "docs/quickstart_debian.md",
        "docs/quickstart_macos.md",
        "dplayer diagnostics --json",
        "docs/PUBLIC_RELEASE_RUNBOOK.md",
    ):
        assert marker in source


def test_readme_links_release_runbook_and_release_notes():
    source = _read("README.md")
    for marker in (
        "docs/PUBLIC_RELEASE_RUNBOOK.md",
        "docs/releases/v0.2.0.md",
    ):
        assert marker in source
