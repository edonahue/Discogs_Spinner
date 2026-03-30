from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def test_validate_tauri_sidecar_contract_script_enforces_expected_naming():
    source = _read("scripts/validate_tauri_sidecar_contract.py")
    for marker in (
        'EXPECTED_EXTERNAL_BIN = "binaries/dplayer-api"',
        'suffix = ".exe" if "-windows-" in target_triple else ""',
        'return f"dplayer-api-{target_triple}{suffix}"',
        'desktop_shell" / "src-tauri" / "tauri.conf.json"',
        'desktop_shell" / "src-tauri" / "binaries"',
        '--target-triple',
        "--require-file",
        "--check-executable",
    ):
        assert marker in source


def test_validate_tauri_linux_bundle_script_checks_deb_and_appimage_contents():
    source = _read("scripts/validate_tauri_linux_bundle.sh")
    for marker in (
        'BUNDLE_ROOT="${ROOT_DIR}/desktop_shell/src-tauri/target/${TARGET_TRIPLE}/release/bundle"',
        'SOURCE_SIDECAR_NAME="dplayer-api-${TARGET_TRIPLE}"',
        'PACKAGED_SIDECAR_NAME="dplayer-api"',
        'dpkg-deb -c "$DEB_FILE"',
        'grep -F "usr/bin/${PACKAGED_SIDECAR_NAME}"',
        '--appimage-extract',
        '-name "${PACKAGED_SIDECAR_NAME}" -o -name "${SOURCE_SIDECAR_NAME}"',
        'PASS: Linux Tauri bundles include ${PACKAGED_SIDECAR_NAME}.',
    ):
        assert marker in source


def test_validate_tauri_macos_bundle_script_checks_dmg_and_app_contents():
    source = _read("scripts/validate_tauri_macos_bundle.sh")
    for marker in (
        'BUNDLE_ROOT="${ROOT_DIR}/desktop_shell/src-tauri/target/${TARGET_TRIPLE}/release/bundle"',
        'DMG_FILE="$(ls -t "${BUNDLE_ROOT}"/dmg/*.dmg 2>/dev/null | head -1 || true)"',
        'SOURCE_SIDECAR_NAME="dplayer-api-${TARGET_TRIPLE}"',
        'PACKAGED_SIDECAR_NAME="dplayer-api"',
        'hdiutil attach -nobrowse -readonly -mountpoint "$MOUNT_DIR" "$DMG_FILE"',
        "Contents/MacOS",
        'PASS: macOS Tauri bundle includes ${PACKAGED_SIDECAR_NAME}.',
    ):
        assert marker in source


def test_validate_tauri_windows_bundle_script_checks_msi_and_nsis_contents():
    source = _read("scripts/validate_tauri_windows_bundle.ps1")
    for marker in (
        '$bundleRoot = Join-Path $rootDir "desktop_shell\\src-tauri\\target\\$TargetTriple\\release\\bundle"',
        '$sourceSidecarName = "dplayer-api-$TargetTriple.exe"',
        '$packagedSidecarName = "dplayer-api.exe"',
        'Get-ChildItem -Path (Join-Path $bundleRoot "msi\\*.msi")',
        'Get-ChildItem -Path (Join-Path $bundleRoot "nsis\\*.exe")',
        "Get-Command 7z",
        'Join-Path ${env:ProgramFiles} "7-Zip\\7z.exe"',
        '$listing = & $sevenZipPath l $Archive.FullName 2>&1',
        'PASS: Windows Tauri bundles include $packagedSidecarName.',
    ):
        assert marker in source


def test_validate_tauri_linux_real_build_script_runs_full_flow():
    source = _read("scripts/validate_tauri_linux_real_build.sh")
    for marker in (
        'PYTHON_BIN="$PYTHON_BIN" ./scripts/build_sidecar.sh --target-triple "$TARGET_TRIPLE"',
        "python3 ./scripts/validate_tauri_sidecar_contract.py \\",
        '"$NPM_BIN" ci',
        '"$NPM_BIN" run build',
        'cargo install tauri-cli --version "^2" --locked',
        'cargo tauri build --target "$TARGET_TRIPLE" --bundles deb,appimage',
        'bash ./scripts/validate_tauri_linux_bundle.sh --target-triple "$TARGET_TRIPLE"',
    ):
        assert marker in source


def test_tauri_linux_build_dockerfile_runs_real_validation_script():
    source = _read("packaging/test/Dockerfile.tauri-linux-build")
    for marker in (
        "FROM node:20-bookworm",
        "libwebkit2gtk-4.1-dev",
        "python3 -m venv /app/venv",
        '/app/venv/bin/pip install -e ".[web]"',
        "bash ./scripts/validate_tauri_linux_real_build.sh \\",
        "--target-triple x86_64-unknown-linux-gnu",
        "--python-bin /app/venv/bin/python",
        "--npm-ci",
    ):
        assert marker in source


def test_installer_workflow_runs_sidecar_and_platform_bundle_validators():
    source = _read(".github/workflows/installer_build.yml")
    for marker in (
        "Validate sidecar contract",
        "Validate downloaded sidecar contract",
        "Validate Linux Tauri bundles",
        "Validate macOS Tauri bundle",
        "Validate Windows Tauri bundles",
        "working-directory: desktop_shell/src-tauri",
        'scripts/validate_tauri_sidecar_contract.py --target-triple "${{ matrix.target_triple }}" --require-file',
        'bash ./scripts/validate_tauri_linux_bundle.sh \\',
        'bash ./scripts/validate_tauri_macos_bundle.sh \\',
        './scripts/validate_tauri_windows_bundle.ps1 `',
    ):
        assert marker in source


def test_tauri_config_uses_top_level_identifier_only():
    payload = json.loads(_read("desktop_shell/src-tauri/tauri.conf.json"))
    assert payload["identifier"] == "com.discogs-spinner.desktop"
    build = payload["build"]
    assert build["beforeBuildCommand"] == "cd ../webapp && npm run build"
    assert build["frontendDist"] == "../../webapp/dist"
    bundle = payload["bundle"]
    assert "identifier" not in bundle
    assert bundle["icon"][0] == "../icons/32x32.png"
