# Recibe la URI de Supabase de forma segura y genera configuraciones locales.

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$backendRoot = Join-Path $projectRoot "backend"
$activeEnv = Join-Path $backendRoot ".env"
$localEnv = Join-Path $backendRoot ".env.local"
$supabaseEnv = Join-Path $backendRoot ".env.supabase"

if (-not (Test-Path -LiteralPath $activeEnv)) {
    throw "No existe backend\.env. Configura primero el backend local."
}

$activeLines = [IO.File]::ReadAllLines($activeEnv)
$activeDatabase = $activeLines | Where-Object { $_ -match '^DATABASE_URL=' } | Select-Object -First 1
if (-not (Test-Path -LiteralPath $localEnv)) {
    if ($activeDatabase -notmatch '@(localhost|127\.0\.0\.1)(:|/)') {
        throw "La configuracion activa no es local y no existe backend\.env.local para respaldarla."
    }
    [IO.File]::WriteAllLines($localEnv, $activeLines, [Text.UTF8Encoding]::new($false))
}

Write-Host "En Supabase abre Connect > Session pooler y copia la URI del puerto 5432."
Write-Host "Pega la URI tal como aparece, conservando [YOUR-PASSWORD]."
Write-Host "La plantilla puede verse porque todavia no contiene la contrasena."
$databaseUrl = Read-Host "URI de Session pooler"
$databaseUrl = $databaseUrl.Trim().Trim('"').Trim("'")
$uriTemplatePattern = '^postgres(?:ql)?(?:\+psycopg)?://[^:@]+:\[YOUR-PASSWORD\]@[^/:]+\.pooler\.supabase\.com:5432/postgres(?:\?.*)?$'
if ($databaseUrl -notmatch $uriTemplatePattern) {
    $databaseUrl = $null
    throw "La plantilla no es valida. Copia URI desde Connect > Session pooler, puerto 5432, sin reemplazar [YOUR-PASSWORD]."
}

$securePassword = Read-Host "Contrasena de la base de datos" -AsSecureString
$passwordPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
try {
    $plainPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($passwordPointer)
    $encodedPassword = [Uri]::EscapeDataString($plainPassword)
    $databaseUrl = $databaseUrl.Replace("[YOUR-PASSWORD]", $encodedPassword)
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($passwordPointer)
    $plainPassword = $null
    $encodedPassword = $null
    $securePassword = $null
}

$sessionPoolerPattern = '^postgres(?:ql)?(?:\+psycopg)?://[^@]+@[^/:]+\.pooler\.supabase\.com:5432/postgres(?:\?.*)?$'
if ($databaseUrl -notmatch $sessionPoolerPattern) {
    $databaseUrl = $null
    throw "No se pudo construir una URI valida para Session pooler."
}

$databaseUrl = $databaseUrl -replace '^postgres(?:ql)?://', 'postgresql+psycopg://'
if ($databaseUrl -notmatch '[?&]sslmode=') {
    $databaseUrl += $(if ($databaseUrl.Contains('?')) { '&sslmode=require' } else { '?sslmode=require' })
}

$baseLines = [IO.File]::ReadAllLines($localEnv)
$foundDatabase = $false
$supabaseLines = foreach ($line in $baseLines) {
    if ($line -match '^DATABASE_URL=') {
        $foundDatabase = $true
        "DATABASE_URL=$databaseUrl"
    } else {
        $line
    }
}
if (-not $foundDatabase) {
    $supabaseLines = @("DATABASE_URL=$databaseUrl") + $supabaseLines
}

[IO.File]::WriteAllLines($supabaseEnv, $supabaseLines, [Text.UTF8Encoding]::new($false))
[IO.File]::WriteAllLines($activeEnv, $supabaseLines, [Text.UTF8Encoding]::new($false))
$databaseUrl = $null
$supabaseLines = $null

Write-Host "Supabase quedo como configuracion activa."
Write-Host "La configuracion local se conserva en backend\.env.local."
Write-Host "Ejecuta .\scripts\initialize-database.ps1 para probar la conexion."
