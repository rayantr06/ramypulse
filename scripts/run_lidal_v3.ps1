param(
  [switch]$DemoAuth
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $repoRoot

if ($DemoAuth) {
  $env:LIDAL_V3_ALLOW_DEV_AUTH = "true"
}

if (-not $env:LIDAL_V3_DB_PATH) {
  $env:LIDAL_V3_DB_PATH = Join-Path $repoRoot "data\lidal_v3.sqlite3"
}

python -m uvicorn services.v3_api.main:app --host 127.0.0.1 --port 8001 --reload
