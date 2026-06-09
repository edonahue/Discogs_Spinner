from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def _read(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def _assert_local_links_exist(rel_paths: tuple[str, ...]) -> None:
    markdown_link_re = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
    image_src_re = re.compile(r'<img[^>]+src="([^"]+)"')

    for rel_path in rel_paths:
        path = ROOT / rel_path
        source = path.read_text(encoding="utf-8")

        for target in markdown_link_re.findall(source):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            clean = target.split("#", 1)[0]
            if not clean:
                continue
            resolved = (path.parent / clean).resolve()
            assert resolved.exists(), f"{rel_path} references missing link target {clean}"

        for target in image_src_re.findall(source):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            clean = target.split("#", 1)[0]
            if not clean:
                continue
            resolved = (path.parent / clean).resolve()
            assert resolved.exists(), f"{rel_path} references missing image asset {clean}"


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
    tracker = _read("docs/V1_READINESS_TRACKER.md")

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

    for marker in (
        "Windows signing wired and verified",
        "macOS signing + notarization wired and verified",
        "Live timing baseline recorded",
        "Small friend/beta cohort reviewed",
        "continue shipping `0.x` releases",
    ):
        assert marker in tracker


def test_release_notes_template_references_quickstarts_and_diagnostics():
    source = _read("docs/RELEASE_NOTES_TEMPLATE.md")
    for marker in (
        "docs/quickstart_windows.md",
        "docs/quickstart_debian.md",
        "docs/quickstart_macos.md",
        "Direct Download Links",
        "dplayer diagnostics --json",
        "docs/PUBLIC_RELEASE_RUNBOOK.md",
    ):
        assert marker in source


def test_readme_links_user_facing_docs_not_internal_runbooks():
    source = _read("README.md")
    for marker in (
        "docs/releases/v0.2.1.md",
        "docs/friend_trial.md",
        "docs/SUPPORT_MATRIX.md",
    ):
        assert marker in source

    for marker in (
        "docs/PUBLIC_RELEASE_RUNBOOK.md",
        "docs/SIGNING.md",
        "docs/RELEASE_TARGET_v1.0.md",
        "docs/V1_READINESS_TRACKER.md",
    ):
        assert marker not in source


def test_readme_promotes_download_now_and_first_launch_value():
    source = _read("README.md")
    for marker in (
        "## Download Now",
        "## First 10 Minutes",
        "Discogs token required",
        "install, paste a Discogs token, sync, browse, and spin",
        "What first launch should feel like:",
        "Discogs.Spinner_0.2.1_x64-setup.exe",
        "Discogs.Spinner_0.2.1_aarch64.dmg",
        "discogs-spinner-gtk4_0.2.1_amd64.deb",
        "Discogs.Spinner_0.2.1_amd64.AppImage",
        "docs/friend_trial.md",
    ):
        assert marker in source


def test_installer_metadata_sells_record_collector_value_and_token_setup():
    tauri_config = _read("desktop_shell/src-tauri/tauri.conf.json")
    desktop_entry = _read("packaging/deb/dplayer-gui.desktop")
    postinst = _read("packaging/deb/postinst")

    for marker in (
        "Browse, spin, and value your Discogs vinyl collection.",
        "Discogs personal access token",
        "sync your collection and wantlist",
        "spin a random record",
    ):
        assert marker in tauri_config

    for marker in (
        "Browse, spin, and value your Discogs vinyl collection",
        "Records;Vinyl;Collection;Wantlist;Market Value",
    ):
        assert marker in desktop_entry

    for marker in (
        "First-time setup for vinyl collectors:",
        "Discogs personal access token",
        "paste the token",
        "browse your records and use Spin",
    ):
        assert marker in postinst


def test_snap_store_listing_metadata_and_assets_are_ready():
    snapcraft = _read("snap/snapcraft.yaml")
    store_submissions = _read("docs/STORE_SUBMISSIONS.md")
    metainfo = _read("packaging/metainfo/com.discogs-spinner.app.metainfo.xml")
    gitignore = _read(".gitignore")

    for marker in (
        "title: Spinner for Discogs",
        "summary: Pick, browse, and value your Discogs vinyl collection",
        "local-first desktop companion for vinyl collectors",
        "personal access token",
        "does not stream audio itself",
        "not affiliated with Discogs",
        "license: MIT",
        "website: https://github.com/edonahue/Discogs_Spinner",
        "source-code: https://github.com/edonahue/Discogs_Spinner",
        "issues: https://github.com/edonahue/Discogs_Spinner/issues",
        "contact: https://github.com/edonahue/Discogs_Spinner/issues",
        "icon: desktop_shell/icons/icon.png",
        "desktop-assets:",
        "usr/share/metainfo/com.discogs-spinner.app.metainfo.xml",
    ):
        assert marker in snapcraft

    for marker in (
        "### Listing metadata",
        "Primary category: `Music and Audio`",
        "Secondary category: `Utilities`",
        "Snap icon: `desktop_shell/icons/icon.png`",
        "docs/media/screenshots/01-browse-gallery.png",
        "docs/media/screenshots/05-setup-wizard.png",
    ):
        assert marker in store_submissions

    for marker in (
        "<summary>Pick, browse, and value your Discogs vinyl collection</summary>",
        "local-first desktop companion for vinyl",
        "personal access token",
        "does not",
        "stream audio itself",
        "not affiliated",
        "Discogs",
    ):
        assert marker in metainfo

    for rel_path in (
        "desktop_shell/icons/icon.png",
        "docs/media/screenshots/01-browse-gallery.png",
        "docs/media/screenshots/02-spin-result.png",
        "docs/media/screenshots/03-market-value-dashboard.png",
        "docs/media/screenshots/04-wantlist-view.png",
        "docs/media/screenshots/05-setup-wizard.png",
    ):
        assert (ROOT / rel_path).exists()

    assert "snapcraft-credentials.txt" in gitignore
    assert "/snapcraft.yaml" in gitignore


def test_active_installer_docs_have_resolvable_local_links_and_assets():
    _assert_local_links_exist(
        (
            "README.md",
            "desktop_shell/README.md",
            "packaging/README.md",
            "scripts/README.md",
            "docs/PUBLIC_RELEASE_RUNBOOK.md",
            "docs/RELEASE_CHECKLIST_WINDOWS_DEBIAN_MACOS.md",
            "docs/RELEASE_NOTES_TEMPLATE.md",
            "docs/STORE_SUBMISSIONS.md",
            "docs/START_HERE.md",
            "docs/friend_trial.md",
            "docs/releases/v0.2.1.md",
            "docs/releases/v0.2.2.md",
            "docs/quickstart_windows.md",
            "docs/quickstart_macos.md",
            "docs/quickstart_debian.md",
        )
    )


def test_start_here_and_friend_trial_are_installer_first():
    start_here = _read("docs/START_HERE.md")
    friend_trial = _read("docs/friend_trial.md")

    assert "A native Windows installer (Tauri app)" in start_here
    assert "A no-install browser fallback" in start_here
    assert "Discogs account and personal access token" in start_here
    assert "install, paste your Discogs token, sync once" in start_here
    assert "Discogs.Spinner_0.2.1_x64-setup.exe" in friend_trial
    assert "discogs-spinner-gtk4_0.2.1_amd64.deb" in friend_trial
    assert "Discogs Spinner_*_x64-setup.exe" not in friend_trial


def test_current_release_notes_pin_verified_stable_asset_links():
    source = _read("docs/releases/v0.2.1.md")
    for marker in (
        "releases/download/v0.2.1/Discogs.Spinner_0.2.1_x64-setup.exe",
        "releases/download/v0.2.1/Discogs.Spinner_0.2.1_x64_en-US.msi",
        "releases/download/v0.2.1/discogs-spinner-gtk4_0.2.1_amd64.deb",
        "releases/download/v0.2.1/discogs-spinner-tauri_0.2.1_amd64.deb",
        "releases/download/v0.2.1/Discogs.Spinner_0.2.1_amd64.AppImage",
        "releases/download/v0.2.1/Discogs.Spinner_0.2.1_aarch64.dmg",
        "releases/download/v0.2.1/Discogs.Spinner_0.2.1_x64.dmg",
        "releases/download/v0.2.1/CHECKSUMS-INSTALLERS.txt",
        "Who This Is For",
        "Discogs personal access token",
        "Installer workflow: pass",
        "Release asset verification: pass",
    ):
        assert marker in source


def test_next_release_notes_prepare_packaging_refresh_assets_and_validation():
    source = _read("docs/releases/v0.2.2.md")
    for marker in (
        "Tag: `v0.2.2`",
        "COSMIC/GTK desktop launch sizing",
        "GTK launcher Python fallback",
        "lazy-loaded gallery album covers",
        "Linux AppStream metadata",
        "lintian",
        "INSTALLER-MANIFEST.txt",
        "releases/download/v0.2.2/Discogs.Spinner_0.2.2_x64-setup.exe",
        "releases/download/v0.2.2/discogs-spinner-gtk4_0.2.2_amd64.deb",
        "scripts/validate_linux_packaging_metadata.py",
        "Installer Build",
    ):
        assert marker in source


def test_release_checklist_requires_package_qa_and_clean_first_run_proof():
    source = _read("docs/RELEASE_CHECKLIST_WINDOWS_DEBIAN_MACOS.md")
    for marker in (
        "v0.2.2",
        "validate_linux_packaging_metadata.py",
        "AppStream metainfo",
        "lintian",
        "Discogs token setup and reaches the token prompt",
        "first sync reaches the collection view or returns a diagnostic failure",
        "INSTALLER-MANIFEST.txt",
    ):
        assert marker in source
