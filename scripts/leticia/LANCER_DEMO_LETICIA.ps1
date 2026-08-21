[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$frontendRoot = Join-Path $repositoryRoot 'frontend'
$vitePath = Join-Path $frontendRoot 'node_modules/vite/bin/vite.js'
$applicationUrl = 'http://127.0.0.1:5173/#/'

if (-not (Test-Path -LiteralPath $vitePath -PathType Leaf)) {
    throw "Vite is not installed at $vitePath. Run INSTALLER_DEMO_LETICIA.ps1 first."
}

$portListener = [System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners() |
    Where-Object { $_.Port -eq 5173 }
if ($portListener) {
    throw 'Port 5173 is already in use. This launcher will not attach to or stop another process.'
}

$nodeCommand = Get-Command 'node.exe' -ErrorAction Stop
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
        throw 'Vite did not become available on http://127.0.0.1:5173 within 30 seconds.'
    }

    Start-Process $applicationUrl
    Read-Host 'The demo is running. Press Enter to stop only this Vite process'
} finally {
    if ($null -ne $viteProcess -and -not $viteProcess.HasExited) {
        Stop-Process -Id $viteProcess.Id -ErrorAction Stop
        Write-Host 'Stopped the Vite process started by this launcher.'
    }
}
