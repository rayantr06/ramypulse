[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$resetUrl = 'http://127.0.0.1:5173/#/demo/reset'

if (-not (Test-Path -LiteralPath (Join-Path $repositoryRoot 'frontend') -PathType Container)) {
    throw "Frontend directory not found: $repositoryRoot"
}

Start-Process $resetUrl
