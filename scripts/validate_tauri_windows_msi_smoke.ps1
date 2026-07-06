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
                $_.Name -match "msiexec|Spinner for Discogs|dplayer-api" -or
                ($_.CommandLine -and $_.CommandLine -match "msiexec|Spinner for Discogs|dplayer-api")
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
        $roots.Add((Join-Path $env:LOCALAPPDATA "Programs\Spinner for Discogs"))
    }
    if ($env:ProgramFiles) {
        $roots.Add((Join-Path $env:ProgramFiles "Spinner for Discogs"))
    }
    if (${env:ProgramFiles(x86)}) {
        $roots.Add((Join-Path ${env:ProgramFiles(x86)} "Spinner for Discogs"))
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

function Get-InstalledSidecarMatches {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Roots,

        [Parameter(Mandatory = $true)]
        [string[]]$Candidates
    )

    return @(
        foreach ($root in $Roots) {
            if (-not (Test-Path $root)) {
                continue
            }
            Get-ChildItem -Path $root -Recurse -File -ErrorAction SilentlyContinue |
                Where-Object { $Candidates -contains $_.Name }
        }
    ) | Sort-Object FullName -Unique
}

function Wait-ForMsiLog {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [int]$TimeoutSeconds = 15
    )

    for ($i = 0; $i -lt $TimeoutSeconds; $i++) {
        if (Test-Path $Path) {
            $logItem = Get-Item -Path $Path
            Write-Host "INFO: MSI log appeared after $($i + 1) seconds ($($logItem.Length) bytes)"
            return $true
        }
        Start-Sleep -Seconds 1
    }

    Write-Host "INFO: MSI log did not appear within ${TimeoutSeconds}s"
    return $false
}

function Get-MsiLogStatus {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path $Path)) {
        return [pscustomobject]@{
            Exists = $false
            Success = $false
            Failed = $false
            Summary = "log-missing"
        }
    }

    $content = Get-Content -Path $Path -Raw -ErrorAction SilentlyContinue
    if (-not $content) {
        return [pscustomobject]@{
            Exists = $true
            Success = $false
            Failed = $false
            Summary = "log-empty"
        }
    }

    $hasProductSuccess = $content.Contains("Product: Spinner for Discogs -- Installation completed successfully.")
    $hasStatusZero = $content.Contains("Installation success or error status: 0.")
    $hasInstallReturn = $content -match 'Action ended .*INSTALL\. Return value 1\.'
    $hasFailure = $content.Contains("Installation failed.") -or
        ($content -match 'Return value 3') -or
        ($content -match 'MainEngineThread is returning [1-9]')

    return [pscustomobject]@{
        Exists = $true
        Success = ($hasProductSuccess -and $hasStatusZero -and $hasInstallReturn)
        Failed = $hasFailure
        Summary = "successMarkers=$hasProductSuccess/$hasStatusZero/$hasInstallReturn failureMarkers=$hasFailure"
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

$quotedMsiPath = "`"$($msiFile.FullName)`""
$quotedMsiLog = "`"$msiLog`""
$msiArgs = @(
    "/i",
    $quotedMsiPath,
    "/qn",
    "/norestart",
    "REBOOT=ReallySuppress",
    "MSIFASTINSTALL=7",
    "/L*V",
    $quotedMsiLog
)

Write-Host "INFO: msiexec argument list:"
foreach ($arg in $msiArgs) {
    Write-Host "  - $arg"
}

$installProcess = Start-Process -FilePath "msiexec.exe" `
    -ArgumentList $msiArgs `
    -PassThru

[void](Wait-ForMsiLog -Path $msiLog -TimeoutSeconds 15)

$msiLogReportedSuccess = $false
$sidecarReported = $false
$completionMode = $null
$sidecarMatches = @()
$installProcessExited = $false
$msiLogStatus = Get-MsiLogStatus -Path $msiLog

for ($elapsed = 0; $elapsed -lt $TimeoutSeconds; $elapsed++) {
    $liveProcess = Get-Process -Id $installProcess.Id -ErrorAction SilentlyContinue
    $installProcessExited = $null -eq $liveProcess

    if ($installProcessExited) {
        $installProcess.Refresh()
    }

    $msiLogStatus = Get-MsiLogStatus -Path $msiLog
    if ($msiLogStatus.Success -and -not $msiLogReportedSuccess) {
        Write-Host "INFO: MSI success markers observed in log: $($msiLogStatus.Summary)"
        $msiLogReportedSuccess = $true
    }
    if ($msiLogStatus.Failed) {
        Write-ProcessSnapshot
        Write-Host "INFO: MSI log reported failure markers: $($msiLogStatus.Summary)"
        Write-MsiLogTail -Path $msiLog
        throw "MSI log reported installation failure."
    }

    $sidecarMatches = @(Get-InstalledSidecarMatches -Roots $installRoots -Candidates $sidecarCandidates)
    if ($sidecarMatches -and -not $sidecarReported) {
        Write-Host "INFO: Installed sidecar observed during smoke check."
        $sidecarReported = $true
    }

    if ($msiLogStatus.Success -and $sidecarMatches) {
        if ($installProcessExited) {
            if ($installProcess.ExitCode -ne 0) {
                Write-ProcessSnapshot
                Write-Host "INFO: MSI log shows success but process exited with code $($installProcess.ExitCode); dumping log."
                Write-MsiLogTail -Path $msiLog
                throw "MSI install process exited with code $($installProcess.ExitCode) despite success markers."
            }
            $completionMode = "process-exit+log+sidecar"
        }
        else {
            $completionMode = "log+sidecar"
        }
        break
    }

    if ($installProcessExited -and $installProcess.ExitCode -ne 0) {
        Write-ProcessSnapshot
        Write-Host "INFO: MSI install failed with exit code $($installProcess.ExitCode); dumping tail of MSI log."
        Write-MsiLogTail -Path $msiLog
        throw "MSI install failed with exit code $($installProcess.ExitCode)."
    }

    Start-Sleep -Seconds 1
}

if (-not $completionMode) {
    Write-ProcessSnapshot
    if (Get-Process -Id $installProcess.Id -ErrorAction SilentlyContinue) {
        Stop-Process -Id $installProcess.Id -Force -ErrorAction SilentlyContinue
    }

    if ($msiLogStatus.Success) {
        Write-Host "INFO: MSI log shows successful install, but no installed sidecar was found before timeout."
        foreach ($root in $installRoots) {
            Write-DirectorySample -Path $root
        }
        Write-MsiLogTail -Path $msiLog
        throw "MSI install completed successfully, but installed tree does not contain $packagedSidecarName or $sourceSidecarName."
    }

    Write-Host "INFO: MSI install timed out before success markers were observed; dumping tail of MSI log if present."
    Write-MsiLogTail -Path $msiLog
    throw "MSI install timed out after ${TimeoutSeconds} seconds."
}

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

Write-Host "INFO: MSI smoke completion mode: $completionMode"
Write-Host "PASS: Windows MSI smoke install includes $packagedSidecarName."
