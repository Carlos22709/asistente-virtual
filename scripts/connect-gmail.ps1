# Ejecuta el flujo OAuth de Gmail con el entorno virtual del proyecto.

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$localPython = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (Test-Path -LiteralPath $localPython) {
    $python = $localPython
} else {
    $python = (Get-Command python -ErrorAction Stop).Source
}

Push-Location (Join-Path $projectRoot "backend")
try {
    & $python -m app.cli.connect_gmail
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
finally {
    Pop-Location
}
