from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def test_rc_release_runbook_contains_tagged_release_steps():
    source = _read("docs/RC_RELEASE_RUNBOOK.md")
    for marker in (
        "Tagged Release",
        ".github/workflows/tagged_release.yml",
        "git tag -a v0.2.0-rc1",
        "git push origin v0.2.0-rc1",
        "CHECKSUMS.ALL.txt",
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
        "docs/RC_RELEASE_RUNBOOK.md",
    ):
        assert marker in source


def test_readme_links_release_runbook_and_template():
    source = _read("README.md")
    for marker in (
        "docs/RC_RELEASE_RUNBOOK.md",
        "docs/RELEASE_NOTES_TEMPLATE.md",
    ):
        assert marker in source
