[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$frontendRoot = Join-Path $repositoryRoot 'frontend'
$environmentFile = Join-Path $frontendRoot '.env.local'

if (-not (Test-Path -LiteralPath $frontendRoot -PathType Container)) {
    throw "Frontend directory not found: $frontendRoot"
}

try {
    $nodeCommand = Get-Command 'node.exe' -ErrorAction Stop
    $npmCommand = Get-Command 'npm.cmd' -ErrorAction Stop
} catch {
    throw 'Node.js 20 or 22 and npm.cmd must be installed and available on PATH.'
}

$nodeVersion = (& $nodeCommand.Source --version).Trim()
if ($nodeVersion -notmatch '^v(20|22)\.') {
    throw "Node.js 20 or 22 is required; found $nodeVersion."
}

Push-Location -LiteralPath $frontendRoot
try {
    Write-Host 'Installing frontend dependencies with npm ci...'
    & $npmCommand.Source ci
    if ($LASTEXITCODE -ne 0) {
        throw "npm ci failed with exit code $LASTEXITCODE."
    }
} finally {
    Pop-Location
}

if (-not (Test-Path $environmentFile)) {
    @(
        'VITE_RAMYPULSE_DEMO_MODE=true'
        'VITE_RAMYPULSE_DEFAULT_TENANT_ID=demo-expo-2026'
        'VITE_LIDAL_V3_API_ENABLED=false'
    ) | Set-Content -LiteralPath $environmentFile -Encoding utf8
    Write-Host "Created demo environment file: $environmentFile"
} else {
    Write-Host "Kept existing environment file unchanged: $environmentFile"
}

Write-Host 'Installation complete. Run LANCER_DEMO_LETICIA.ps1 to open the demo.'
