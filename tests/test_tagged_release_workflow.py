from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_tagged_release_workflow_builds_and_publishes_tag_assets():
    source = (
        ROOT / ".github" / "workflows" / "tagged_release.yml"
    ).read_text(encoding="utf-8")

    for marker in (
        "name: Legacy Tarball Release",
        "workflow_dispatch:",
        "build-release-artifacts:",
        "publish-release:",
        "ubuntu-latest",
        "macos-latest",
        "windows-latest",
        "./scripts/build_artifacts.sh all",
        "CHECKSUMS-${{ matrix.os }}.txt",
        "softprops/action-gh-release@v2",
        "github.event.inputs.tag",
        "legacy tarballs",
    ):
        assert marker in source
