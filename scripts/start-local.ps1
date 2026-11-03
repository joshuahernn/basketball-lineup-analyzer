param(
    [string]$PostgresBin = 'C:/Program Files/PostgreSQL/18/bin'
)

. (Join-Path $PSScriptRoot 'local-db.ps1')

$cluster = Join-Path $projectRoot '.local/postgres'
$pgCtl = Join-Path $PostgresBin 'pg_ctl.exe'

& $pgCtl -D $cluster status *> $null

if ($LASTEXITCODE -ne 0) {
    & $pgCtl -D $cluster -l (Join-Path $projectRoot '.local/postgres.log') -o '-h 127.0.0.1 -p 55432' start

    if ($LASTEXITCODE -ne 0) {
        throw 'Local PostgreSQL could not start.'
    }
}

if (-not (Test-Path -LiteralPath (Join-Path $env:FRONTEND_DIST_DIR 'index.html'))) {
    Push-Location (Join-Path $projectRoot 'frontend')

    try {
        npm.cmd run build

        if ($LASTEXITCODE -ne 0) {
            throw 'Frontend build failed.'
        }
    } finally {
        Pop-Location
    }
}

Push-Location (Join-Path $projectRoot 'backend')

try {
    & (Join-Path $projectRoot '.venv/Scripts/python.exe') manage.py runserver 127.0.0.1:8000 --noreload
} finally {
    Pop-Location
}
