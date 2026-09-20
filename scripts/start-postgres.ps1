# Inicia la instancia local de PostgreSQL usada por el proyecto.

$ErrorActionPreference = "Stop"
$postgresBin = Join-Path $env:LOCALAPPDATA "Programs\PostgreSQL\18\bin"
$dataDirectory = Join-Path $env:LOCALAPPDATA "PostgreSQL\18\data"
$serverLog = Join-Path $dataDirectory "server.log"
$postgresPort = 5433

& (Join-Path $postgresBin "pg_isready.exe") -h 127.0.0.1 -p $postgresPort *> $null
if ($LASTEXITCODE -eq 0) {
    Write-Host "PostgreSQL ya está iniciado en 127.0.0.1:$postgresPort."
    exit 0
}

& (Join-Path $postgresBin "pg_ctl.exe") -D $dataDirectory -l $serverLog -o "-p $postgresPort" start
if ($LASTEXITCODE -ne 0) {
    throw "No fue posible iniciar PostgreSQL. Revisa $serverLog"
}

Write-Host "PostgreSQL iniciado en 127.0.0.1:$postgresPort."
