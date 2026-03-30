Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

param(
    [Parameter(Mandatory = $true)]
    [string]$TargetTriple
)

$rootDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$bundleRoot = Join-Path $rootDir "desktop_shell\src-tauri\target\$TargetTriple\release\bundle"
$sourceSidecarName = "dplayer-api-$TargetTriple.exe"
$packagedSidecarName = "dplayer-api.exe"

$msiFile = Get-ChildItem -Path (Join-Path $bundleRoot "msi\*.msi") -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if (-not $msiFile) {
    throw "No Windows .msi bundle found under $bundleRoot\msi."
}

$nsisFile = Get-ChildItem -Path (Join-Path $bundleRoot "nsis\*.exe") -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if (-not $nsisFile) {
    throw "No Windows NSIS .exe bundle found under $bundleRoot\nsis."
}

$sevenZip = Get-Command 7z -ErrorAction SilentlyContinue
$sevenZipPath = if ($sevenZip) {
    $sevenZip.Source
}
else {
    $fallback7z = Join-Path ${env:ProgramFiles} "7-Zip\7z.exe"
    if (Test-Path $fallback7z) {
        $fallback7z
    }
    else {
        throw "7z is required to inspect Windows installer contents on the GitHub runner."
    }
}

function Test-ArchiveContainsSidecar {
    param(
        [Parameter(Mandatory = $true)]
        [System.IO.FileInfo]$Archive
    )

    $listing = & $sevenZipPath l $Archive.FullName 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to inspect archive contents for $($Archive.FullName)."
    }

    foreach ($candidate in @($packagedSidecarName, $sourceSidecarName)) {
        if ($listing -match [Regex]::Escape($candidate)) {
            return
        }
    }

    throw "$($Archive.Name) does not appear to include $packagedSidecarName or $sourceSidecarName."
}

Test-ArchiveContainsSidecar -Archive $msiFile
Test-ArchiveContainsSidecar -Archive $nsisFile

Write-Host "PASS: Windows Tauri bundles include $packagedSidecarName."
