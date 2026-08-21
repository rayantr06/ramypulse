[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$frontendRoot = Join-Path $repositoryRoot 'frontend'
$vitePath = Join-Path $frontendRoot 'node_modules/vite/bin/vite.js'
$applicationUrl = 'http://127.0.0.1:5173/#/'

if (-not (Test-Path -LiteralPath $frontendRoot -PathType Container)) {
    throw "Le dossier frontend est introuvable : $frontendRoot. Verifiez que le dossier du projet est complet, puis relancez ce script."
}

if (-not (Test-Path -LiteralPath $vitePath -PathType Leaf)) {
    throw "Vite n'est pas installe : $vitePath. Executez d'abord INSTALLER_DEMO_LETICIA.ps1, puis relancez ce script."
}

$portListener = [System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners() |
    Where-Object { $_.Port -eq 5173 }
if ($portListener) {
    throw "Le port 5173 est deja utilise. Fermez l'application qui utilise ce port, puis relancez LANCER_DEMO_LETICIA.ps1."
}

$nodeCommand = Get-Command 'node.exe' -ErrorAction SilentlyContinue
if ($null -eq $nodeCommand) {
    throw 'Node.js est introuvable. Installez Node.js 20 ou 22, puis executez INSTALLER_DEMO_LETICIA.ps1.'
}

$nodeVersion = (& $nodeCommand.Source --version).Trim()
if ($nodeVersion -notmatch '^v(20|22)\.') {
    throw "La version $nodeVersion de Node.js n'est pas prise en charge. Installez Node.js 20 ou 22, puis executez INSTALLER_DEMO_LETICIA.ps1."
}

$viteProcess = $null

try {
    $viteProcess = Start-Process -FilePath $nodeCommand.Source `
        -ArgumentList @($vitePath, '--host', '127.0.0.1', '--port', '5173') `
        -WorkingDirectory $frontendRoot `
        -WindowStyle Hidden `
        -PassThru

    $serverReady = $false
    $deadline = (Get-Date).AddSeconds(30)
    do {
        try {
            Invoke-WebRequest -Uri $applicationUrl -UseBasicParsing -TimeoutSec 2 | Out-Null
            $serverReady = $true
            break
        } catch {
            Start-Sleep -Milliseconds 500
        }
    } while ((Get-Date) -lt $deadline)

    if (-not $serverReady) {
        throw "Le serveur Vite n'est pas disponible sur http://127.0.0.1:5173 apres 30 secondes. Verifiez l'installation avec INSTALLER_DEMO_LETICIA.ps1, puis relancez ce script."
    }

    Start-Process $applicationUrl
    Read-Host 'La demonstration est ouverte. Appuyez sur Entree pour arreter uniquement ce processus Vite'
} finally {
    if ($null -ne $viteProcess -and -not $viteProcess.HasExited) {
        Stop-Process -Id $viteProcess.Id -ErrorAction Stop
        Write-Host 'Le processus Vite demarre par ce lanceur a ete arrete.'
    }
}
