# Shared environment for this checkout's isolated local PostgreSQL database.
$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$localDatabase = Join-Path $projectRoot '.local/database.json'

if (-not (Test-Path -LiteralPath $localDatabase)) {
    throw 'Local database configuration is missing: .local/database.json.'
}

$databaseConfig = Get-Content -LiteralPath $localDatabase -Raw | ConvertFrom-Json

$env:PGDATABASE = $databaseConfig.database
$env:PGUSER = $databaseConfig.user
$env:PGPASSWORD = $databaseConfig.password
$env:PGHOST = $databaseConfig.host
$env:PGPORT = [string]$databaseConfig.port

# Do not accidentally inherit a remote connection when running the local demo.
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue

$env:PYTHONDONTWRITEBYTECODE = '1'
$env:DJANGO_DEBUG = 'true'
$env:DJANGO_ALLOWED_HOSTS = 'localhost,127.0.0.1,[::1],testserver'
$env:FRONTEND_DIST_DIR = Join-Path $projectRoot 'frontend/dist/frontend/browser'
