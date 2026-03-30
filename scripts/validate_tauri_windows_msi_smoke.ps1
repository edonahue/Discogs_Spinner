param(
    [Parameter(Mandatory = $true)]
    [string]$TargetTriple,

    [int]$TimeoutSeconds = 600
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-MsiLogTail {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path $Path)) {
        Write-Host "INFO: MSI log does not exist at $Path"
        return
    }

    $logItem = Get-Item -Path $Path
    Write-Host "INFO: MSI log exists at $Path ($($logItem.Length) bytes)"
    Get-Content -Path $Path -Tail 200 | ForEach-Object { Write-Host $_ }
}

function Write-ProcessSnapshot {
    Write-Host "INFO: Process snapshot for MSI-related processes:"

    $processes = @(
        Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
            Where-Object {
                $_.Name -match "msiexec|Discogs Spinner|dplayer-api" -or
                ($_.CommandLine -and $_.CommandLine -match "msiexec|Discogs Spinner|dplayer-api")
            } |
            Sort-Object ProcessId
    )

    if (-not $processes) {
        Write-Host "  - no matching processes found"
        return
    }

    foreach ($process in $processes) {
        Write-Host "  - pid=$($process.ProcessId) parent=$($process.ParentProcessId) name=$($process.Name)"
        if ($process.CommandLine) {
            Write-Host "    command=$($process.CommandLine)"
        }
    }
}

function Get-InstallRoots {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FallbackRoot
    )

    $roots = [System.Collections.Generic.List[string]]::new()
    $roots.Add($FallbackRoot)

    if ($env:LOCALAPPDATA) {
        $roots.Add((Join-Path $env:LOCALAPPDATA "Programs\Discogs Spinner"))
    }
    if ($env:ProgramFiles) {
        $roots.Add((Join-Path $env:ProgramFiles "Discogs Spinner"))
    }
    if (${env:ProgramFiles(x86)}) {
        $roots.Add((Join-Path ${env:ProgramFiles(x86)} "Discogs Spinner"))
    }

    return @(
        $roots |
            Where-Object { $_ } |
            Select-Object -Unique
    )
}

function Write-DirectorySample {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path $Path)) {
        Write-Host "INFO: Install root missing: $Path"
        return
    }

    Write-Host "INFO: Installed file sample under $Path"
    Get-ChildItem -Path $Path -Recurse -File -ErrorAction SilentlyContinue |
        Select-Object -First 50 |
        ForEach-Object {
            $relativePath = [System.IO.Path]::GetRelativePath($Path, $_.FullName)
            Write-Host "  - $relativePath"
        }
}

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

$installRoots = @(Get-InstallRoots -FallbackRoot $installRoot)
Write-Host "INFO: Candidate install roots:"
foreach ($path in $installRoots) {
    Write-Host "  - $path"
}

$installProcess = Start-Process -FilePath "msiexec.exe" `
    -ArgumentList @("/i", $msiFile.FullName, "/qn", "/norestart", "REBOOT=ReallySuppress", "MSIFASTINSTALL=7", "/L*V", $msiLog) `
    -PassThru

try {
    Wait-Process -Id $installProcess.Id -Timeout $TimeoutSeconds -ErrorAction Stop
}
catch {
    Write-ProcessSnapshot
    Stop-Process -Id $installProcess.Id -Force -ErrorAction SilentlyContinue
    Write-Host "INFO: MSI install timed out; dumping tail of MSI log if present."
    Write-MsiLogTail -Path $msiLog
    throw "MSI install timed out after ${TimeoutSeconds} seconds."
}

if ($installProcess.ExitCode -ne 0) {
    Write-ProcessSnapshot
    Write-Host "INFO: MSI install failed with exit code $($installProcess.ExitCode); dumping tail of MSI log."
    Write-MsiLogTail -Path $msiLog
    throw "MSI install failed with exit code $($installProcess.ExitCode)."
}

$sidecarMatches = @(
    foreach ($root in $installRoots) {
        if (-not (Test-Path $root)) {
            continue
        }
        Get-ChildItem -Path $root -Recurse -File -ErrorAction SilentlyContinue |
            Where-Object { $sidecarCandidates -contains $_.Name }
    }
) | Sort-Object FullName -Unique
if (-not $sidecarMatches) {
    Write-Host "INFO: No installed sidecar match found. Installed file sample:"
    foreach ($root in $installRoots) {
        Write-DirectorySample -Path $root
    }
    Write-MsiLogTail -Path $msiLog
    throw "Installed MSI tree does not contain $packagedSidecarName or $sourceSidecarName."
}

Write-Host "INFO: Installed sidecar paths:"
foreach ($match in $sidecarMatches) {
    $installRootForMatch = $installRoots | Where-Object { $match.FullName.StartsWith($_, [System.StringComparison]::OrdinalIgnoreCase) } | Select-Object -First 1
    if ($installRootForMatch) {
        $relativePath = [System.IO.Path]::GetRelativePath($installRootForMatch, $match.FullName)
        Write-Host "  - $installRootForMatch :: $relativePath"
    }
    else {
        Write-Host "  - $($match.FullName)"
    }
}

Write-Host "PASS: Windows MSI smoke install includes $packagedSidecarName."
