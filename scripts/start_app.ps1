param()

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$logDir = Join-Path $projectRoot "run-logs"
$apiPidFile = Join-Path $logDir "api.pid"
$webPidFile = Join-Path $logDir "web.pid"
$runtimeFile = Join-Path $logDir "runtime.json"

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Get-PythonPath {
    $venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        return $venvPython
    }

    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        return $pythonCommand.Source
    }

    throw "Python was not found. Install Python first, or create a .venv in the project root."
}

function Test-ExistingProcess {
    param(
        [string]$PidFile,
        [string]$ExpectedCommandLine = ""
    )

    if (-not (Test-Path $PidFile)) {
        return $null
    }

    $rawPid = (Get-Content $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1).Trim()
    if (-not $rawPid) {
        Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
        return $null
    }

    $process = Get-Process -Id ([int]$rawPid) -ErrorAction SilentlyContinue
    if ($process) {
        if ($ExpectedCommandLine) {
            try {
                $cimProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $rawPid"
                $commandLine = $cimProcess.CommandLine
                if (-not $commandLine -or $commandLine -notlike "*$ExpectedCommandLine*") {
                    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
                    return $null
                }
            } catch {
                Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
                return $null
            }
        }
        return $process
    }

    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    return $null
}

function Test-PortAvailable {
    param(
        [int]$Port
    )

    try {
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $Port)
        $listener.Start()
        return $true
    } catch {
        return $false
    } finally {
        if ($listener) {
            $listener.Stop()
        }
    }
}

function Get-FreePort {
    param(
        [int]$StartPort,
        [int[]]$ExcludePorts = @()
    )

    for ($port = $StartPort; $port -lt ($StartPort + 200); $port++) {
        if ($ExcludePorts -contains $port) {
            continue
        }

        if (Test-PortAvailable -Port $port) {
            return $port
        }
    }

    throw ("No free port found starting from {0}." -f $StartPort)
}

function Load-RuntimeState {
    if (-not (Test-Path $runtimeFile)) {
        return $null
    }

    try {
        return Get-Content $runtimeFile -Raw | ConvertFrom-Json
    } catch {
        return $null
    }
}

function Save-RuntimeState {
    param(
        [int]$ApiPort,
        [int]$WebPort
    )

    $payload = @{
        api_port = $ApiPort
        web_port = $WebPort
        api_base_url = "http://127.0.0.1:$ApiPort"
        web_url = "http://127.0.0.1:$WebPort"
    }
    $payload | ConvertTo-Json | Set-Content -Path $runtimeFile
}

function Start-ServiceProcess {
    param(
        [string]$ServiceName,
        [string]$PidFile,
        [string]$ArgumentLine,
        [string]$ExpectedCommandLine,
        [string]$OutLog,
        [string]$ErrLog
    )

    $existing = Test-ExistingProcess -PidFile $PidFile -ExpectedCommandLine $ExpectedCommandLine
    if ($existing) {
        Write-Host ("{0} is already running. PID={1}" -f $ServiceName, $existing.Id)
        return $existing
    }

    $pythonPath = Get-PythonPath
    $process = Start-Process `
        -FilePath $pythonPath `
        -ArgumentList $ArgumentLine `
        -WorkingDirectory $projectRoot `
        -RedirectStandardOutput $OutLog `
        -RedirectStandardError $ErrLog `
        -WindowStyle Hidden `
        -PassThru

    Set-Content -Path $PidFile -Value $process.Id
    Write-Host ("{0} started. PID={1}" -f $ServiceName, $process.Id)
    return $process
}

if (-not (Test-Path (Join-Path $projectRoot ".env"))) {
    throw ".env was not found. Copy .env.example to .env and set DEEPSEEK_API_KEY first."
}

$existingApi = Test-ExistingProcess -PidFile $apiPidFile -ExpectedCommandLine "uvicorn app.api.main:app"
$existingWeb = Test-ExistingProcess -PidFile $webPidFile -ExpectedCommandLine "streamlit run web/streamlit_app.py"
$existingRuntime = Load-RuntimeState

if ($existingApi -and $existingWeb -and $existingRuntime) {
    Write-Host ("FastAPI is already running. PID={0}" -f $existingApi.Id)
    Write-Host ("Streamlit is already running. PID={0}" -f $existingWeb.Id)
    Write-Host ("Web UI: {0}" -f $existingRuntime.web_url)
    Write-Host ("API Docs: http://127.0.0.1:{0}/docs" -f $existingRuntime.api_port)
    Start-Process $existingRuntime.web_url
    exit 0
}

$apiPort = Get-FreePort -StartPort 8000
$webPort = Get-FreePort -StartPort 8501 -ExcludePorts @($apiPort)
Save-RuntimeState -ApiPort $apiPort -WebPort $webPort

$apiProcess = Start-ServiceProcess `
    -ServiceName "FastAPI" `
    -PidFile $apiPidFile `
    -ArgumentLine "-m uvicorn app.api.main:app --host 127.0.0.1 --port $apiPort" `
    -ExpectedCommandLine "uvicorn app.api.main:app" `
    -OutLog (Join-Path $logDir "api.out.log") `
    -ErrLog (Join-Path $logDir "api.err.log")

$webProcess = Start-ServiceProcess `
    -ServiceName "Streamlit" `
    -PidFile $webPidFile `
    -ArgumentLine "-m streamlit run web/streamlit_app.py --server.address 127.0.0.1 --server.port $webPort" `
    -ExpectedCommandLine "streamlit run web/streamlit_app.py" `
    -OutLog (Join-Path $logDir "web.out.log") `
    -ErrLog (Join-Path $logDir "web.err.log")

Write-Host "Waiting for services to start..."
Start-Sleep -Seconds 4

Start-Process "http://127.0.0.1:$webPort"

Write-Host ""
Write-Host "Project started."
Write-Host ("Web UI: http://127.0.0.1:{0}" -f $webPort)
Write-Host ("API Docs: http://127.0.0.1:{0}/docs" -f $apiPort)
Write-Host "To stop services, run stop_app.bat"
