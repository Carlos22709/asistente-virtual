# Copia datos de PostgreSQL local a Supabase mediante la utilidad del backend.

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$localEnv = Join-Path $projectRoot "backend\.env.local"
$supabaseEnv = Join-Path $projectRoot "backend\.env.supabase"

if (-not (Test-Path -LiteralPath $localEnv) -or -not (Test-Path -LiteralPath $supabaseEnv)) {
    throw "Faltan .env.local o .env.supabase. Ejecuta primero configure-supabase.ps1."
}

& (Join-Path $PSScriptRoot "start-postgres.ps1")
$confirmation = Read-Host "Escribe MIGRAR para copiar los datos locales a un Supabase vacío"
if ($confirmation -cne "MIGRAR") {
    Write-Host "Migración cancelada."
    exit 0
}

Push-Location (Join-Path $projectRoot "backend")
try {
    & $python -m app.cli.migrate_to_supabase
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
finally {
    Pop-Location
}
