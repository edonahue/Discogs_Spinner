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


def test_build_sidecar_script_uses_platform_specific_add_data_separator():
    source = _read("scripts/build_sidecar.sh")
    for marker in (
        'ADD_DATA_SEPARATOR=":"',
        'ADD_DATA_SEPARATOR=";"',
        'SOURCE_DATA_DIR="${ROOT_DIR}/src/discogs_player/data"',
        'SOURCE_DATA_DIR="$(cygpath -w "${SOURCE_DATA_DIR}")"',
        '--add-data "${SOURCE_DATA_DIR}${ADD_DATA_SEPARATOR}discogs_player/data"',
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
    param_index = source.index("param(")
    strict_mode_index = source.index("Set-StrictMode -Version Latest")
    assert param_index < strict_mode_index

    for marker in (
        'function Write-DirectoryInventory',
        'function New-TempDirectory',
        'function Write-ExtractedInventory',
        'function Find-SidecarMatches',
        'function Write-WixInventory',
        'Write-Host "INFO: Windows bundle root: $bundleRoot"',
        '$bundleRoot = Join-Path $rootDir "desktop_shell\\src-tauri\\target\\$TargetTriple\\release\\bundle"',
        '$wixRoot = Join-Path $rootDir "desktop_shell\\src-tauri\\target\\$TargetTriple\\release\\wix"',
        '$sourceSidecarName = "dplayer-api-$TargetTriple.exe"',
        '$packagedSidecarName = "dplayer-api.exe"',
        '$sidecarCandidates = @($packagedSidecarName, $sourceSidecarName)',
        '$msiCandidates = Write-DirectoryInventory -Label "MSI bundle directory" -Path $msiDir -Filter "*.msi"',
        '$nsisCandidates = Write-DirectoryInventory -Label "NSIS bundle directory" -Path $nsisDir -Filter "*.exe"',
        "Get-Command 7z",
        'Join-Path ${env:ProgramFiles} "7-Zip\\7z.exe"',
        'Write-Host "INFO: Using 7z at $sevenZipPath"',
        'Write-Host "INFO: START MSI metadata check"',
        'Write-Host "INFO: Inspecting WiX metadata for $($Archive.FullName)"',
        'Write-Host "INFO: WiX metadata lines containing sidecar references:"',
        '$matchesToLog = @($matches | Select-Object -First 2)',
        'Write-Host "INFO: Additional WiX sidecar matches omitted:',
        'Write-WixInventory -Path $wixRoot',
        'Write-Host "INFO: END MSI metadata check"',
        'Write-Host "INFO: START NSIS extraction check"',
        'Expected WiX metadata under $wixRoot.',
        'in WiX metadata.',
        'Write-Host "INFO: Inspecting $Kind archive $($Archive.FullName)"',
        'Write-Host "INFO: Extracting NSIS archive from $($Archive.FullName) to $extractRoot"',
        '$output = & $sevenZipPath x -y "-o$extractRoot" $Archive.FullName 2>&1',
        'Write-Host "INFO: Extracted $Kind paths containing dplayer-api:"',
        'Write-Host "INFO: $Kind sidecar verification succeeded."',
        'Write-Host "INFO: END NSIS extraction check"',
        'Write-ExtractedInventory -Label $Kind -Path $extractRoot',
        'Remove-TempDirectories',
        'after extraction.',
        'PASS: Windows Tauri bundles include $packagedSidecarName.',
    ):
        assert marker in source


def test_validate_tauri_windows_msi_smoke_script_uses_bounded_install_and_log_dump():
    source = _read("scripts/validate_tauri_windows_msi_smoke.ps1")
    param_index = source.index("param(")
    strict_mode_index = source.index("Set-StrictMode -Version Latest")
    assert param_index < strict_mode_index

    for marker in (
        'function Write-MsiLogTail',
        'function Write-ProcessSnapshot',
        'function Get-InstallRoots',
        'function Write-DirectorySample',
        'function Get-InstalledSidecarMatches',
        'function Wait-ForMsiLog',
        'function Get-MsiLogStatus',
        '[int]$TimeoutSeconds = 600',
        '$artifactsRoot = Join-Path $rootDir "build\\windows-msi-smoke"',
        '$installRoot = Join-Path $artifactsRoot "install-root"',
        '$msiLog = Join-Path $artifactsRoot "msiexec.log"',
        '$installRoots = @(Get-InstallRoots -FallbackRoot $installRoot)',
        '$quotedMsiPath = "`"$($msiFile.FullName)`""',
        '$quotedMsiLog = "`"$msiLog`""',
        '$msiArgs = @(',
        'Write-Host "INFO: msiexec argument list:"',
        'Start-Process -FilePath "msiexec.exe"',
        '"/norestart"',
        '"REBOOT=ReallySuppress"',
        '"MSIFASTINSTALL=7"',
        '[void](Wait-ForMsiLog -Path $msiLog -TimeoutSeconds 15)',
        'Write-Host "INFO: MSI log appeared after $($i + 1) seconds',
        'Write-Host "INFO: MSI log did not appear within ${TimeoutSeconds}s"',
        '$msiLogReportedSuccess = $false',
        '$sidecarReported = $false',
        '$completionMode = $null',
        'for ($elapsed = 0; $elapsed -lt $TimeoutSeconds; $elapsed++)',
        '$msiLogStatus = Get-MsiLogStatus -Path $msiLog',
        'Write-Host "INFO: MSI success markers observed in log:',
        '$sidecarMatches = @(Get-InstalledSidecarMatches -Roots $installRoots -Candidates $sidecarCandidates)',
        'Write-Host "INFO: Installed sidecar observed during smoke check."',
        '$completionMode = "process-exit+log+sidecar"',
        '$completionMode = "log+sidecar"',
        'Write-Host "INFO: MSI log reported failure markers:',
        'MSI log reported installation failure.',
        'MSI install completed successfully, but installed tree does not contain',
        'Write-ProcessSnapshot',
        'if (Get-Process -Id $installProcess.Id -ErrorAction SilentlyContinue)',
        'Stop-Process -Id $installProcess.Id -Force',
        'Write-MsiLogTail -Path $msiLog',
        'Write-DirectorySample -Path $root',
        'Write-Host "INFO: MSI smoke completion mode: $completionMode"',
        'PASS: Windows MSI smoke install includes $packagedSidecarName.',
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
        "macos-15-intel",
        "Log workflow ref and commit",
        "github.sha=${{ github.sha }}",
        "github.ref=${{ github.ref }}",
        "git rev-parse HEAD",
        "Validate sidecar contract",
        "Validate downloaded sidecar contract",
        "Validate Linux Tauri bundles",
        "Validate macOS Tauri bundle",
        "Validate Windows Tauri bundles",
        "Validate release notes file",
        'test -f "docs/releases/${GITHUB_REF_NAME}.md"',
        "body_path: docs/releases/${{ github.ref_name }}.md",
        "CHECKSUMS-INSTALLERS.txt",
        "working-directory: desktop_shell/src-tauri",
        'scripts/validate_tauri_sidecar_contract.py --target-triple "${{ matrix.target_triple }}" --require-file',
        'bash ./scripts/validate_tauri_linux_bundle.sh \\',
        'bash ./scripts/validate_tauri_macos_bundle.sh \\',
        './scripts/validate_tauri_windows_bundle.ps1 `',
    ):
        assert marker in source


def test_windows_msi_smoke_workflow_runs_manual_and_scheduled_windows_install_smoke():
    source = _read(".github/workflows/windows_msi_smoke.yml")
    for marker in (
        'name: Windows MSI Smoke',
        'workflow_dispatch:',
        'cron: "17 5 * * *"',
        'runs-on: windows-2022',
        'timeout-minutes: 30',
        'run: ./scripts/build_sidecar.sh --target-triple "x86_64-pc-windows-msvc"',
        'python3 scripts/validate_tauri_sidecar_contract.py \\',
        'cargo tauri build --target x86_64-pc-windows-msvc --bundles msi',
        'timeout-minutes: 15',
        './scripts/validate_tauri_windows_msi_smoke.ps1 `',
        'name: windows-msi-smoke-logs',
        'build/windows-msi-smoke/**',
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
