param(
    [Parameter(Mandatory = $true)]
    [string]$TargetTriple,

    [int]$TimeoutSeconds = 600
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$rootDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$bundleRoot = Join-Path $rootDir "desktop_shell\src-tauri\target\$TargetTriple\release\bundle"
$msiDir = Join-Path $bundleRoot "msi"
$packagedSidecarName = "dplayer-api.exe"
$sourceSidecarName = "dplayer-api-$TargetTriple.exe"
$sidecarCandidates = @($packagedSidecarName, $sourceSidecarName)
$artifactsRoot = Join-Path $rootDir "build\windows-msi-smoke"
$installRoot = Join-Path $artifactsRoot "install-root"
$msiLog = Join-Path $artifactsRoot "msiexec.log"

New-Item -ItemType Directory -Path $artifactsRoot -Force | Out-Null
if (Test-Path $installRoot) {
    Remove-Item -Path $installRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $installRoot -Force | Out-Null

$msiFile = Get-ChildItem -Path (Join-Path $msiDir "*.msi") -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if (-not $msiFile) {
    throw "No Windows .msi bundle found under $msiDir."
}

Write-Host "INFO: Windows MSI smoke root: $artifactsRoot"
Write-Host "INFO: Using MSI bundle $($msiFile.FullName)"
Write-Host "INFO: Install root: $installRoot"
Write-Host "INFO: MSI log path: $msiLog"
Write-Host "INFO: MSI runtime timeout: ${TimeoutSeconds}s"

$installProcess = Start-Process -FilePath "msiexec.exe" `
    -ArgumentList @("/i", $msiFile.FullName, "/qn", "INSTALLDIR=$installRoot", "/L*V", $msiLog) `
    -PassThru

try {
    Wait-Process -Id $installProcess.Id -Timeout $TimeoutSeconds -ErrorAction Stop
}
catch {
    Stop-Process -Id $installProcess.Id -Force -ErrorAction SilentlyContinue
    Write-Host "INFO: MSI install timed out; dumping tail of MSI log if present."
    if (Test-Path $msiLog) {
        Get-Content -Path $msiLog -Tail 200 | ForEach-Object { Write-Host $_ }
    }
    throw "MSI install timed out after ${TimeoutSeconds} seconds."
}

if ($installProcess.ExitCode -ne 0) {
    Write-Host "INFO: MSI install failed with exit code $($installProcess.ExitCode); dumping tail of MSI log."
    if (Test-Path $msiLog) {
        Get-Content -Path $msiLog -Tail 200 | ForEach-Object { Write-Host $_ }
    }
    throw "MSI install failed with exit code $($installProcess.ExitCode)."
}

$sidecarMatches = @(
    Get-ChildItem -Path $installRoot -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object { $sidecarCandidates -contains $_.Name } |
        Sort-Object FullName
)
if (-not $sidecarMatches) {
    Write-Host "INFO: No installed sidecar match found. Installed file sample:"
    Get-ChildItem -Path $installRoot -Recurse -File -ErrorAction SilentlyContinue |
        Select-Object -First 50 |
        ForEach-Object {
            $relativePath = [System.IO.Path]::GetRelativePath($installRoot, $_.FullName)
            Write-Host "  - $relativePath"
        }
    throw "Installed MSI tree does not contain $packagedSidecarName or $sourceSidecarName."
}

Write-Host "INFO: Installed sidecar paths:"
foreach ($match in $sidecarMatches) {
    $relativePath = [System.IO.Path]::GetRelativePath($installRoot, $match.FullName)
    Write-Host "  - $relativePath"
}

Write-Host "PASS: Windows MSI smoke install includes $packagedSidecarName."
