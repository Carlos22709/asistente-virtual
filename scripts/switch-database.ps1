# Alterna la configuracion activa entre PostgreSQL local y Supabase.

param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("Local", "Supabase")]
    [string]$Target
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$backendRoot = Join-Path $projectRoot "backend"
$source = if ($Target -eq "Local") {
    Join-Path $backendRoot ".env.local"
} else {
    Join-Path $backendRoot ".env.supabase"
}
$active = Join-Path $backendRoot ".env"

if (-not (Test-Path -LiteralPath $source)) {
    throw "No existe $source. Ejecuta primero configure-supabase.ps1."
}

Copy-Item -LiteralPath $source -Destination $active -Force
Write-Host "Base activa: $Target. Reinicia el backend para aplicar el cambio."
