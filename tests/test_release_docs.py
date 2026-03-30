from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def test_public_release_runbook_contains_installer_release_steps():
    source = _read("docs/PUBLIC_RELEASE_RUNBOOK.md")
    for marker in (
        "Installer Build",
        "Windows MSI Smoke",
        ".github/workflows/installer_build.yml",
        "git tag -a v0.2.0",
        "git push origin v0.2.0",
        "CHECKSUMS-INSTALLERS.txt",
        "RELEASE_NOTES_TEMPLATE.md",
    ):
        assert marker in source


def test_support_matrix_and_v1_release_target_define_first_class_surfaces():
    support_matrix = _read("docs/SUPPORT_MATRIX.md")
    release_target = _read("docs/RELEASE_TARGET_v1.0.md")

    for marker in (
        "CLI (`dplayer`)",
        "Native installers",
        "Windows 10/11 x64",
        "macOS 13+",
        "Debian 12+ / Ubuntu equivalent",
        "Web app / local API",
    ):
        assert marker in support_matrix

    for marker in (
        "reliable local-first collector app",
        "stable CLI plus native installers",
        "web/API parity is not a `1.0` blocker",
        "Windows and macOS installers are signed",
        "1.0.0-rc1",
    ):
        assert marker in release_target


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
        "docs/friend_trial.md",
        "docs/SUPPORT_MATRIX.md",
        "docs/RELEASE_TARGET_v1.0.md",
    ):
        assert marker in source
