# Crea y valida las tablas usando la base configurada actualmente.

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    throw "No existe el entorno .venv del proyecto."
}

Push-Location (Join-Path $projectRoot "backend")
try {
    & $python -m app.cli.initialize_database
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
finally {
    Pop-Location
}
