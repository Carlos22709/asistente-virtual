# Inicia FastAPI en la red local con la configuracion activa.

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$backendEnv = Join-Path $projectRoot "backend\.env"

if (-not (Test-Path -LiteralPath $backendEnv)) {
    throw "No existe backend\.env. Crea la configuración antes de iniciar el backend."
}

$databaseLine = Get-Content -LiteralPath $backendEnv | Where-Object { $_ -match '^DATABASE_URL=' } | Select-Object -First 1
if (-not $databaseLine) {
    throw "backend\.env no contiene DATABASE_URL."
}

if ($databaseLine -match '@(localhost|127\.0\.0\.1)(:|/)') {
    & (Join-Path $PSScriptRoot "start-postgres.ps1")
} else {
    Write-Host "Base remota configurada; no se iniciará PostgreSQL local."
}
Set-Location (Join-Path $projectRoot "backend")
& (Join-Path $projectRoot ".venv\Scripts\python.exe") -m uvicorn app.main:app --host 0.0.0.0 --port 3000 --reload
