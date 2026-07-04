param()

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$logDir = Join-Path $projectRoot "run-logs"
$runtimeFile = Join-Path $logDir "runtime.json"
$pidFiles = @(
    @{ Name = "FastAPI"; Path = (Join-Path $logDir "api.pid") },
    @{ Name = "Streamlit"; Path = (Join-Path $logDir "web.pid") }
)

foreach ($entry in $pidFiles) {
    $serviceName = $entry.Name
    $pidFile = $entry.Path

    if (-not (Test-Path $pidFile)) {
        Write-Host ("{0}: no PID file found, skipped." -f $serviceName)
        continue
    }

    $rawPid = (Get-Content $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1).Trim()
    if (-not $rawPid) {
        Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
        Write-Host ("{0}: empty PID file removed." -f $serviceName)
        continue
    }

    $process = Get-Process -Id ([int]$rawPid) -ErrorAction SilentlyContinue
    if ($process) {
        Stop-Process -Id $process.Id -Force
        Write-Host ("{0} stopped. PID={1}" -f $serviceName, $process.Id)
    } else {
        Write-Host ("{0}: process not found, PID file removed." -f $serviceName)
    }

    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "All services stopped."

if (Test-Path $runtimeFile) {
    Remove-Item $runtimeFile -Force -ErrorAction SilentlyContinue
}
