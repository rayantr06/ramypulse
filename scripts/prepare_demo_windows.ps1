[CmdletBinding()]
param(
    [switch]$SkipDependencies
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$frontendRoot = Join-Path $projectRoot "frontend"
$venvRoot = Join-Path $projectRoot ".venv"
$venvPython = Join-Path $venvRoot "Scripts\python.exe"

Write-Host "Préparation de LIDAL Pulse Demo" -ForegroundColor Cyan
Write-Host "Projet : $projectRoot"

$systemPython = (Get-Command python -ErrorAction Stop).Source
$npmCommand = (Get-Command npm.cmd -ErrorAction Stop).Source

if (-not $SkipDependencies) {
    if (-not (Test-Path -LiteralPath $venvPython)) {
        Write-Host "Création de l'environnement Python .venv..." -ForegroundColor Yellow
        & $systemPython -m venv $venvRoot
    }

    Write-Host "Installation des dépendances Python..." -ForegroundColor Yellow
    & $venvPython -m pip install --upgrade pip
    & $venvPython -m pip install -r (Join-Path $projectRoot "requirements.txt")

    Write-Host "Installation des dépendances frontend..." -ForegroundColor Yellow
    Push-Location $frontendRoot
    try {
        & $npmCommand install
    }
    finally {
        Pop-Location
    }
}

$pythonCommand = if (Test-Path -LiteralPath $venvPython) { $venvPython } else { $systemPython }
$rootEnvPath = Join-Path $projectRoot ".env"
$frontendEnvPath = Join-Path $frontendRoot ".env.local"

if (-not (Test-Path -LiteralPath $rootEnvPath)) {
    @(
        "SAFE_EXPO_CLIENT_ID=demo-expo-2026"
        "RAMYPULSE_RUNTIME_MODE=offline"
    ) | Set-Content -LiteralPath $rootEnvPath -Encoding utf8
    Write-Host "Configuration backend locale créée." -ForegroundColor Green
}

if (-not (Test-Path -LiteralPath $frontendEnvPath)) {
    Copy-Item -LiteralPath (Join-Path $frontendRoot ".env.example") -Destination $frontendEnvPath
    Write-Host "Configuration frontend locale créée." -ForegroundColor Green
}

Write-Host "Création de la base de démonstration assainie..." -ForegroundColor Yellow
Push-Location $projectRoot
try {
    & $pythonCommand scripts/seed_demo.py --tenant demo-expo-2026 --reset --api-key dev --verbatims 200
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "Préparation terminée." -ForegroundColor Green
Write-Host "Lancez ensuite : powershell -ExecutionPolicy Bypass -File .\scripts\start_demo_windows.ps1"
