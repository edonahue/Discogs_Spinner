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
$sidecarCandidates = @($packagedSidecarName, $sourceSidecarName)
$tempRoots = [System.Collections.Generic.List[string]]::new()

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

function New-TempDirectory {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Prefix
    )

    $path = Join-Path ([System.IO.Path]::GetTempPath()) "$Prefix-$([System.Guid]::NewGuid().ToString('N'))"
    New-Item -ItemType Directory -Path $path -Force | Out-Null
    $tempRoots.Add($path)
    return $path
}

function Remove-TempDirectories {
    foreach ($path in $tempRoots) {
        if (Test-Path $path) {
            Remove-Item -Path $path -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}

function Write-ExtractedInventory {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Label,

        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    Write-Host "INFO: $Label extracted tree root: $Path"
    if (-not (Test-Path $Path)) {
        Write-Host "INFO: $Label extracted tree root does not exist."
        return
    }

    $items = Get-ChildItem -Path $Path -Recurse -File -ErrorAction SilentlyContinue |
        Select-Object -First 25
    if (-not $items) {
        Write-Host "INFO: $Label extracted tree has no files."
        return
    }

    Write-Host "INFO: $Label extracted tree sample:"
    foreach ($item in $items) {
        $relativePath = [System.IO.Path]::GetRelativePath($Path, $item.FullName)
        Write-Host "  - $relativePath"
    }
}

function Find-SidecarMatches {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path $Path)) {
        return @()
    }

    return @(
        Get-ChildItem -Path $Path -Recurse -File -ErrorAction SilentlyContinue |
            Where-Object { $sidecarCandidates -contains $_.Name } |
            Sort-Object FullName
    )
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

function Expand-MsiArchive {
    param(
        [Parameter(Mandatory = $true)]
        [System.IO.FileInfo]$Archive
    )

    $extractRoot = New-TempDirectory -Prefix "dplayer-msi"
    $targetDir = Join-Path $extractRoot "target"
    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null

    Write-Host "INFO: Extracting MSI administratively from $($Archive.FullName) to $targetDir"
    $process = Start-Process -FilePath "msiexec.exe" `
        -ArgumentList @("/a", $Archive.FullName, "/qn", "TARGETDIR=$targetDir") `
        -NoNewWindow `
        -PassThru `
        -Wait
    if ($process.ExitCode -ne 0) {
        throw "Failed to extract MSI contents from $($Archive.FullName) with exit code $($process.ExitCode)."
    }

    return $targetDir
}

function Expand-NsisArchive {
    param(
        [Parameter(Mandatory = $true)]
        [System.IO.FileInfo]$Archive
    )

    $extractRoot = New-TempDirectory -Prefix "dplayer-nsis"
    Write-Host "INFO: Extracting NSIS archive from $($Archive.FullName) to $extractRoot"
    $output = & $sevenZipPath x -y "-o$extractRoot" $Archive.FullName 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "INFO: 7z output:"
        $output | ForEach-Object { Write-Host $_ }
        throw "Failed to extract NSIS contents from $($Archive.FullName)."
    }

    return $extractRoot
}

function Test-ExtractedArchiveContainsSidecar {
    param(
        [Parameter(Mandatory = $true)]
        [System.IO.FileInfo]$Archive,

        [Parameter(Mandatory = $true)]
        [string]$Kind,

        [Parameter(Mandatory = $true)]
        [scriptblock]$ExpandArchive
    )

    Write-Host "INFO: Inspecting $Kind archive $($Archive.FullName)"
    $extractRoot = & $ExpandArchive $Archive
    $sidecarMatches = Find-SidecarMatches -Path $extractRoot
    if ($sidecarMatches) {
        Write-Host "INFO: Extracted $Kind paths containing dplayer-api:"
        foreach ($match in $sidecarMatches) {
            $relativePath = [System.IO.Path]::GetRelativePath($extractRoot, $match.FullName)
            Write-Host "  - $relativePath"
        }
        return
    }

    Write-ExtractedInventory -Label $Kind -Path $extractRoot
    throw "$($Archive.Name) does not appear to include $packagedSidecarName or $sourceSidecarName after extraction."
}

try {
    Test-ExtractedArchiveContainsSidecar -Archive $msiFile -Kind "MSI" -ExpandArchive ${function:Expand-MsiArchive}
    Test-ExtractedArchiveContainsSidecar -Archive $nsisFile -Kind "NSIS" -ExpandArchive ${function:Expand-NsisArchive}
}
finally {
    Remove-TempDirectories
}

Write-Host "PASS: Windows Tauri bundles include $packagedSidecarName."
