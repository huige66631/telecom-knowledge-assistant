param()

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$logDir = Join-Path $projectRoot "run-logs"
$runtimeFile = Join-Path $logDir "runtime.json"
$pidFiles = @(
    @{ Name = "FastAPI"; Path = (Join-Path $logDir "api.pid"); Expected = "uvicorn app.api.main:app" },
    @{ Name = "Streamlit"; Path = (Join-Path $logDir "web.pid"); Expected = "streamlit run web/streamlit_app.py" }
)

foreach ($entry in $pidFiles) {
    $serviceName = $entry.Name
    $pidFile = $entry.Path
    $expectedCommand = $entry.Expected

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
        $shouldStop = $false
        try {
            $cimProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $rawPid"
            $commandLine = $cimProcess.CommandLine
            if ($commandLine -and $commandLine -like "*$expectedCommand*") {
                $shouldStop = $true
            }
        } catch {
            $shouldStop = $false
        }

        if ($shouldStop) {
            Stop-Process -Id $process.Id -Force
            Write-Host ("{0} stopped. PID={1}" -f $serviceName, $process.Id)
        } else {
            Write-Host ("{0}: PID {1} does not belong to this project, skipped." -f $serviceName, $rawPid)
        }
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
