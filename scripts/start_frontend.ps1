param(
    [string]$HostName = "127.0.0.1",
    [int]$Port = 5173,
    [int]$PortProbeCount = 20,
    [switch]$CheckOnly
)

$ErrorActionPreference = "Stop"

function Write-LauncherStatus {
    param([string]$Message)
    Write-Host "[frontend-launcher] $Message"
}

function Test-FrontendReady {
    param([string]$Url)

    try {
        $Response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
        $Content = [string]$Response.Content
        return $Content.Contains('<div id="root"')
    }
    catch {
        return $false
    }
}

function Test-TcpPortOpen {
    param(
        [string]$HostName,
        [int]$Port
    )

    $Client = [System.Net.Sockets.TcpClient]::new()
    try {
        $Connect = $Client.BeginConnect($HostName, $Port, $null, $null)
        if (-not $Connect.AsyncWaitHandle.WaitOne(250, $false)) {
            return $false
        }
        $Client.EndConnect($Connect)
        return $Client.Connected
    }
    catch {
        return $false
    }
    finally {
        $Client.Close()
    }
}

function Find-FrontendLaunchTarget {
    param(
        [string]$HostName,
        [int]$RequestedPort,
        [int]$PortProbeCount
    )

    for ($Offset = 0; $Offset -le $PortProbeCount; $Offset++) {
        $CandidatePort = $RequestedPort + $Offset
        $CandidateUrl = "http://$HostName`:$CandidatePort/"

        if (Test-FrontendReady -Url $CandidateUrl) {
            return @{
                Port = $CandidatePort
                Url = $CandidateUrl
                Reuse = $true
            }
        }

        if (-not (Test-TcpPortOpen -HostName $HostName -Port $CandidatePort)) {
            if ($Offset -gt 0) {
                Write-LauncherStatus "port $RequestedPort is occupied by another service; using $CandidatePort"
            }
            return @{
                Port = $CandidatePort
                Url = $CandidateUrl
                Reuse = $false
            }
        }

        Write-LauncherStatus "port $CandidatePort is occupied by a different service; trying next port"
    }

    throw "frontend_port_unavailable: requested=$RequestedPort probe_count=$PortProbeCount"
}

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$FrontendDir = Join-Path $RepoRoot "frontend"
$PackageJson = Join-Path $FrontendDir "package.json"
$NodeModules = Join-Path $FrontendDir "node_modules"

if (-not (Test-Path -LiteralPath $PackageJson)) {
    throw "frontend_package_json_missing: $PackageJson"
}

$NpmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
if (-not $NpmCommand) {
    $NpmCommand = Get-Command npm -ErrorAction SilentlyContinue
}
if (-not $NpmCommand) {
    throw "npm_not_found: install Node.js/npm before launching the frontend"
}

if (-not (Test-Path -LiteralPath $NodeModules)) {
    throw "frontend_dependencies_missing: run npm install in $FrontendDir before launching the frontend"
}

$LaunchTarget = Find-FrontendLaunchTarget -HostName $HostName -RequestedPort $Port -PortProbeCount $PortProbeCount
$Port = [int]$LaunchTarget.Port
$Url = [string]$LaunchTarget.Url

if ($CheckOnly) {
    Write-LauncherStatus "check ok"
    Write-LauncherStatus "frontend_dir=$FrontendDir"
    Write-LauncherStatus "url=$Url"
    exit 0
}

if ($LaunchTarget.Reuse) {
    Write-LauncherStatus "current project already running at $Url"
    Start-Process $Url
    exit 0
}

Write-LauncherStatus "starting Vite dev server at $Url"
$CommandLine = "/k cd /d `"$FrontendDir`" && `"$($NpmCommand.Source)`" run dev -- --host $HostName --port $Port --strictPort"
Start-Process -FilePath "cmd.exe" -ArgumentList $CommandLine -WindowStyle Normal

Write-LauncherStatus "waiting for frontend to become ready"
for ($Attempt = 1; $Attempt -le 45; $Attempt++) {
    if (Test-FrontendReady -Url $Url) {
        Write-LauncherStatus "frontend ready; opening browser"
        Start-Process $Url
        exit 0
    }
    Start-Sleep -Seconds 1
}

throw "frontend_start_timeout: $Url"
