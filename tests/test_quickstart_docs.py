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


def test_quickstarts_link_clean_machine_validation_checklists():
    windows = _read("docs/quickstart_windows.md")
    macos = _read("docs/quickstart_macos.md")
    debian = _read("docs/quickstart_debian.md")

    assert "validation/windows_tauri_ftux.md" in windows
    assert "validation/macos_installer_ftux.md" in macos
    assert "validation/debian_installer_ftux.md" in debian
    assert "releases/download/v0.2.1/Discogs.Spinner_0.2.1_x64-setup.exe" in windows
    assert "releases/download/v0.2.1/Discogs.Spinner_0.2.1_x64_en-US.msi" in windows
    assert "releases/download/v0.2.1/Discogs.Spinner_0.2.1_aarch64.dmg" in macos
    assert "releases/download/v0.2.1/Discogs.Spinner_0.2.1_x64.dmg" in macos
    assert "releases/download/v0.2.1/discogs-spinner-gtk4_0.2.1_amd64.deb" in debian
    assert "releases/download/v0.2.1/discogs-spinner-tauri_0.2.1_amd64.deb" in debian
    assert "releases/download/v0.2.1/Discogs.Spinner_0.2.1_amd64.AppImage" in debian
    assert "releases/download/v0.2.1/CHECKSUMS-INSTALLERS.txt" in windows
    assert "releases/download/v0.2.1/CHECKSUMS-INSTALLERS.txt" in debian


def test_quickstarts_call_out_recommended_installer_and_first_run_success():
    windows = _read("docs/quickstart_windows.md")
    macos = _read("docs/quickstart_macos.md")
    debian = _read("docs/quickstart_debian.md")

    for source in (windows, macos, debian):
        assert "What success looks like:" in source

    assert "Recommended installer:" in windows
    assert "Recommended for most modern Macs:" in macos
    assert "GTK desktop `.deb` installer (recommended)" in debian
    assert "start with the GTK `.deb`" in debian


def test_readme_links_os_quickstarts():
    source = _read("README.md")
    for marker in (
        "## OS Quickstarts",
        "docs/quickstart_windows.md",
        "docs/quickstart_debian.md",
        "docs/quickstart_macos.md",
    ):
        assert marker in source
