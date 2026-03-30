param(
    [Parameter(Mandatory = $true)]
    [string]$TargetTriple
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$rootDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$bundleRoot = Join-Path $rootDir "desktop_shell\src-tauri\target\$TargetTriple\release\bundle"
$sourceSidecarName = "dplayer-api-$TargetTriple.exe"
$packagedSidecarName = "dplayer-api.exe"

function Write-DirectoryInventory {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Label,

        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [string]$Filter
    )

    Write-Host "INFO: $Label path: $Path"
    $items = Get-ChildItem -Path (Join-Path $Path $Filter) -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending
    if (-not $items) {
        Write-Host "INFO: $Label path has no matches for $Filter."
        return @()
    }

    Write-Host "INFO: $Label matches:"
    foreach ($item in $items) {
        Write-Host "  - $($item.Name)"
    }

    return @($items)
}

Write-Host "INFO: Windows bundle root: $bundleRoot"
$msiDir = Join-Path $bundleRoot "msi"
$nsisDir = Join-Path $bundleRoot "nsis"
$msiCandidates = Write-DirectoryInventory -Label "MSI bundle directory" -Path $msiDir -Filter "*.msi"
$nsisCandidates = Write-DirectoryInventory -Label "NSIS bundle directory" -Path $nsisDir -Filter "*.exe"

$msiFile = $msiCandidates | Select-Object -First 1
if (-not $msiFile) {
    throw "No Windows .msi bundle found under $msiDir."
}

$nsisFile = $nsisCandidates | Select-Object -First 1
if (-not $nsisFile) {
    throw "No Windows NSIS .exe bundle found under $nsisDir."
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
Write-Host "INFO: Using 7z at $sevenZipPath"

function Test-ArchiveContainsSidecar {
    param(
        [Parameter(Mandatory = $true)]
        [System.IO.FileInfo]$Archive
    )

    Write-Host "INFO: Inspecting archive $($Archive.FullName)"
    $listing = & $sevenZipPath l $Archive.FullName 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "INFO: 7z output:"
        $listing | ForEach-Object { Write-Host $_ }
        throw "Failed to inspect archive contents for $($Archive.FullName)."
    }

    $sidecarMatches = @($listing | Where-Object { $_ -match "dplayer-api" })
    if ($sidecarMatches) {
        Write-Host "INFO: Archive entries containing dplayer-api:"
        $sidecarMatches | ForEach-Object { Write-Host $_ }
    }
    else {
        Write-Host "INFO: No archive entries containing dplayer-api were found."
    }

    foreach ($candidate in @($packagedSidecarName, $sourceSidecarName)) {
        if ($listing -match [Regex]::Escape($candidate)) {
            Write-Host "INFO: Matched sidecar candidate $candidate in $($Archive.Name)."
            return
        }
    }

    throw "$($Archive.Name) does not appear to include $packagedSidecarName or $sourceSidecarName."
}

Test-ArchiveContainsSidecar -Archive $msiFile
Test-ArchiveContainsSidecar -Archive $nsisFile

Write-Host "PASS: Windows Tauri bundles include $packagedSidecarName."
