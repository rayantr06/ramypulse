[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$resetUrl = 'http://127.0.0.1:5173/#/demo/reset'

if (-not (Test-Path -LiteralPath (Join-Path $repositoryRoot 'frontend') -PathType Container)) {
    throw "Le dossier frontend est introuvable : $repositoryRoot. Verifiez que le dossier du projet est complet, puis relancez ce script."
}

Start-Process $resetUrl
