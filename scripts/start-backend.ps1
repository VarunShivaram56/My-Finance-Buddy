param(
    [switch]$NoReload
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $projectRoot "backend"
$requirementsFile = Join-Path $backendDir "requirements.txt"
$venvDir = Join-Path $backendDir ".venv"
$venvPython = Join-Path $venvDir "Scripts\\python.exe"
$moduleCheck = "import fastapi, uvicorn, sqlalchemy, pdfplumber, chromadb, httpx, pydantic_settings"
$backendPort = 8000
$backendHealthUrl = "http://127.0.0.1:$backendPort/health"

function Test-Interpreter {
    param(
        [string]$Command,
        [string[]]$Arguments
    )

    try {
        & $Command @Arguments "-c" $moduleCheck | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

function Invoke-Checked {
    param(
        [string]$Command,
        [string[]]$Arguments
    )

    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $Command $($Arguments -join ' ')"
    }
}

function Resolve-BaseInterpreter {
    $candidates = @(
        @{ command = "py"; args = @("-3.13") },
        @{ command = "python"; args = @() }
    )

    foreach ($candidate in $candidates) {
        try {
            $candidateArgs = $candidate.args + @("--version")
            & $candidate.command @candidateArgs | Out-Null
            return $candidate
        }
        catch {
            continue
        }
    }

    throw "Python was not found. Install Python 3.10+ and try again."
}

function Resolve-BackendPython {
    if (Test-Path $venvPython) {
        if (Test-Interpreter -Command $venvPython -Arguments @()) {
            return @{ command = $venvPython; args = @() }
        }
    }

    $base = Resolve-BaseInterpreter
    if (Test-Interpreter -Command $base.command -Arguments $base.args) {
        return $base
    }

    Write-Host "Creating backend virtual environment and installing dependencies..."
    Invoke-Checked -Command $base.command -Arguments ($base.args + @("-m", "venv", $venvDir))
    Invoke-Checked -Command $venvPython -Arguments @("-m", "pip", "install", "--disable-pip-version-check", "-r", $requirementsFile)
    return @{ command = $venvPython; args = @() }
}

function Get-PortOwner {
    try {
        return Get-NetTCPConnection -LocalPort $backendPort -State Listen -ErrorAction Stop | Select-Object -First 1
    }
    catch {
        return $null
    }
}

function Test-BackendHealth {
    try {
        $response = Invoke-WebRequest -Uri $backendHealthUrl -UseBasicParsing -TimeoutSec 3
        return $response.Content -like '*"status":"ok"*'
    }
    catch {
        return $false
    }
}

try {
    $existing = Get-PortOwner
    if ($existing) {
        if (Test-BackendHealth) {
            Write-Host "Backend already running on port $backendPort (PID $($existing.OwningProcess)). Reusing existing process."
            if ($existing.OwningProcess) {
                Wait-Process -Id $existing.OwningProcess
            }
            else {
                while ($true) {
                    Start-Sleep -Seconds 60
                }
            }
            exit 0
        }

        throw "Port $backendPort is already in use by PID $($existing.OwningProcess), but it is not responding as My Finance Buddy. Stop that process and run npm run dev again."
    }

    $python = Resolve-BackendPython
    $pythonArgs = $python.args
    $uvicornArgs = @("-m", "uvicorn", "main:app", "--app-dir", $backendDir, "--host", "127.0.0.1", "--port", "$backendPort")
    if (-not $NoReload) {
        $uvicornArgs += "--reload"
    }

    Write-Host "Starting backend with $($python.command) $($python.args -join ' ')"
    & $python.command @pythonArgs @uvicornArgs
    exit $LASTEXITCODE
}
catch {
    Write-Error $_
    exit 1
}
