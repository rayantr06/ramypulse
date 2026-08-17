[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$frontendRoot = Join-Path $projectRoot "frontend"
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$pythonCommand = if (Test-Path -LiteralPath $venvPython) {
    $venvPython
} else {
    (Get-Command python -ErrorAction Stop).Source
}
$nodeCommand = (Get-Command node.exe -ErrorAction Stop).Source
$viteEntry = Join-Path $frontendRoot "node_modules\vite\bin\vite.js"

if (-not (Test-Path -LiteralPath (Join-Path $projectRoot "data\ramypulse.db"))) {
    throw "Base de démonstration absente. Exécutez d'abord scripts\prepare_demo_windows.ps1."
}
if (-not (Test-Path -LiteralPath $viteEntry)) {
    throw "Dépendances frontend absentes. Exécutez d'abord scripts\prepare_demo_windows.ps1."
}

$backend = $null
$frontend = $null

try {
    Write-Host "Démarrage de l'API LIDAL Pulse..." -ForegroundColor Cyan
    $backendArguments = @{
        FilePath = $pythonCommand
        ArgumentList = @("-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "8000")
        WorkingDirectory = $projectRoot
        WindowStyle = "Hidden"
        PassThru = $true
    }
    $backend = Start-Process @backendArguments

    Write-Host "Démarrage de l'interface..." -ForegroundColor Cyan
    $frontendArguments = @{
        FilePath = $nodeCommand
        ArgumentList = @($viteEntry, "--host", "127.0.0.1")
        WorkingDirectory = $frontendRoot
        WindowStyle = "Hidden"
        PassThru = $true
    }
    $frontend = Start-Process @frontendArguments

    $healthUrl = "http://127.0.0.1:8000/api/health"
    $ready = $false
    for ($attempt = 1; $attempt -le 30; $attempt++) {
        try {
            $health = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 2
            if ($health.status -eq "ok") {
                $ready = $true
                break
            }
        }
        catch {
            Start-Sleep -Seconds 1
        }
    }

    if (-not $ready) {
        throw "L'API n'a pas répondu après 30 secondes."
    }

    $appUrl = "http://127.0.0.1:5173/#/"
    Write-Host ""
    Write-Host "LIDAL Pulse est prêt : $appUrl" -ForegroundColor Green
    Start-Process $appUrl
    Read-Host "Appuyez sur Entrée pour arrêter la démonstration"
}
finally {
    foreach ($process in @($frontend, $backend)) {
        if ($null -ne $process -and -not $process.HasExited) {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        }
    }
    Write-Host "Démonstration arrêtée."
}
