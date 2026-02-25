from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _script_text(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def test_build_artifacts_script_supports_core_plus_and_os_normalization():
    source = _script_text("scripts/build_artifacts.sh")
    for marker in (
        "Usage: $0 [all|core|plus]",
        "build_profile \"core\" \".\"",
        "build_profile \"plus\" \".[spotify]\"",
        "normalize_os_name()",
        "Linux*) echo \"linux\"",
        "Darwin*) echo \"macos\"",
        "MINGW*|MSYS*|Windows_NT",
        "PIP_NO_BUILD_ISOLATION",
        "PIP_WHEEL_NO_DEPS",
        "--no-build-isolation",
        "--no-deps",
        "discogs_player-${profile}-${PLATFORM_TAG}.tar.gz",
    ):
        assert marker in source
