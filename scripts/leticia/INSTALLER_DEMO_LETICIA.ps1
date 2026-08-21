[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$frontendRoot = Join-Path $repositoryRoot 'frontend'
$clientRoot = Join-Path $frontendRoot 'client'
$environmentFile = Join-Path $clientRoot '.env.local'
$nodeVersionRules = Join-Path $PSScriptRoot 'NODE_VERSION_DEMO.ps1'

if (-not (Test-Path -LiteralPath $nodeVersionRules -PathType Leaf)) {
    throw "Le verificateur de version Node.js est introuvable : $nodeVersionRules. Verifiez que le dossier du projet est complet, puis relancez ce script."
}
. $nodeVersionRules

if (-not (Test-Path -LiteralPath $frontendRoot -PathType Container)) {
    throw "Le dossier frontend est introuvable : $frontendRoot. Verifiez que le dossier du projet est complet, puis relancez ce script."
}

$nodeCommand = Get-Command 'node.exe' -ErrorAction SilentlyContinue
if ($null -eq $nodeCommand) {
    throw 'Node.js est introuvable. Installez Node.js 20.19.0 minimum ou Node.js 22.12.0 minimum, puis relancez INSTALLER_DEMO_LETICIA.ps1.'
}

$npmCommand = Get-Command 'npm.cmd' -ErrorAction SilentlyContinue
if ($null -eq $npmCommand) {
    throw 'npm.cmd est introuvable. Reinstallez Node.js 20.19.0 minimum ou Node.js 22.12.0 minimum, puis relancez INSTALLER_DEMO_LETICIA.ps1.'
}

$nodeVersion = (& $nodeCommand.Source --version).Trim()
if (-not (Test-LeticiaNodeVersion -Version $nodeVersion)) {
    throw "La version $nodeVersion de Node.js n'est pas prise en charge par Vite 7.3.1. Installez Node.js 20.19.0 minimum ou Node.js 22.12.0 minimum, puis relancez INSTALLER_DEMO_LETICIA.ps1."
}

Push-Location -LiteralPath $frontendRoot
try {
    Write-Host 'Installation des dependances frontend avec npm ci...'
    & $npmCommand.Source ci
    if ($LASTEXITCODE -ne 0) {
        throw "npm ci a echoue (code $LASTEXITCODE). Verifiez votre connexion Internet et les droits d'acces au dossier frontend, puis relancez INSTALLER_DEMO_LETICIA.ps1."
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
    Write-Host "Fichier d'environnement de demonstration cree : $environmentFile"
} else {
    Write-Host "Fichier d'environnement existant conserve sans modification : $environmentFile"
}

Write-Host 'Installation terminee. Executez LANCER_DEMO_LETICIA.ps1 pour ouvrir la demonstration.'
