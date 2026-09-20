# Detiene de forma ordenada la instancia local de PostgreSQL.

$ErrorActionPreference = "Stop"
$postgresBin = Join-Path $env:LOCALAPPDATA "Programs\PostgreSQL\18\bin"
$dataDirectory = Join-Path $env:LOCALAPPDATA "PostgreSQL\18\data"

& (Join-Path $postgresBin "pg_ctl.exe") -D $dataDirectory stop
