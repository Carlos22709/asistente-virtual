# Diagnostica y levanta Ollama, FastAPI y Expo desde un solo comando.

[CmdletBinding()]
param([switch]$CheckOnly)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$backendScript = Join-Path $PSScriptRoot "start-backend.ps1"
$mobileScript = Join-Path $PSScriptRoot "start-mobile.ps1"
$healthUrl = "http://127.0.0.1:3000/health"
$ollamaUrl = "http://127.0.0.1:11434/api/tags"
$metroUrl = "http://127.0.0.1:8081/status"

function Test-Endpoint {
    param([string]$Uri, [int]$TimeoutSeconds = 3)
    try { return Invoke-RestMethod -Uri $Uri -TimeoutSec $TimeoutSeconds -ErrorAction Stop }
    catch { return $null }
}

function Wait-Endpoint {
    param([string]$Uri, [int]$Attempts)
    for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
        $response = Test-Endpoint -Uri $Uri -TimeoutSeconds 2
        if ($null -ne $response) { return $response }
        Start-Sleep -Seconds 1
    }
    return $null
}

Write-Host ""
Write-Host "Kirby - inicio del entorno local" -ForegroundColor Cyan
Write-Host "Proyecto: $projectRoot"
Write-Host ""

$requiredPaths = @(
    @{ Path = (Join-Path $projectRoot ".venv\Scripts\python.exe"); Label = "Entorno virtual de Python" },
    @{ Path = (Join-Path $projectRoot "backend\.env"); Label = "Configuracion del backend" },
    @{ Path = (Join-Path $projectRoot "mobile\package.json"); Label = "Proyecto movil" },
    @{ Path = (Join-Path $projectRoot "mobile\node_modules\.bin\expo.cmd"); Label = "Dependencias moviles" },
    @{ Path = $backendScript; Label = "Script del backend" },
    @{ Path = $mobileScript; Label = "Script del cliente movil" }
)
foreach ($item in $requiredPaths) {
    if (-not (Test-Path -LiteralPath $item.Path)) {
        throw "$($item.Label) no esta disponible: $($item.Path)"
    }
    Write-Host "[OK] $($item.Label)" -ForegroundColor Green
}

$ollama = Test-Endpoint -Uri $ollamaUrl
if ($null -eq $ollama -and -not $CheckOnly) {
    $ollamaCommand = Get-Command ollama.exe, ollama -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $ollamaCommand) { throw "Ollama no esta instalado o no esta disponible en PATH." }
    Write-Host "[INICIO] Levantando Ollama..." -ForegroundColor Yellow
    Start-Process -FilePath $ollamaCommand.Source -ArgumentList "serve" -WindowStyle Hidden | Out-Null
    $ollama = Wait-Endpoint -Uri $ollamaUrl -Attempts 20
    if ($null -eq $ollama) { throw "Ollama no respondio despues de 20 segundos." }
}
if ($null -eq $ollama) {
    Write-Host "[PENDIENTE] Ollama no esta respondiendo." -ForegroundColor Yellow
}
else {
    Write-Host "[OK] Ollama esta respondiendo." -ForegroundColor Green
    if (@($ollama.models | Where-Object { $_.name -like "llama3.2*" }).Count -gt 0) {
        Write-Host "[OK] Modelo llama3.2 disponible." -ForegroundColor Green
    }
    else { Write-Warning "Falta el modelo llama3.2. Ejecuta: ollama pull llama3.2" }
}

$tailscaleScript = Join-Path $PSScriptRoot "tailscale-status.ps1"
if (Test-Path -LiteralPath $tailscaleScript) {
    try { & $tailscaleScript }
    catch {
        Write-Warning "No se pudo consultar Tailscale: $($_.Exception.Message)"
        Write-Warning "Expo intentara usar la red local como alternativa."
    }
}

$backend = Test-Endpoint -Uri $healthUrl
if ($null -ne $backend) {
    Write-Host "[OK] FastAPI ya esta respondiendo en $healthUrl." -ForegroundColor Green
}
else {
    $portOwner = Get-NetTCPConnection -State Listen -LocalPort 3000 -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -ne $portOwner) {
        throw "El puerto 3000 esta ocupado por el proceso $($portOwner.OwningProcess), pero /health no responde."
    }
    if ($CheckOnly) {
        Write-Host "[PENDIENTE] FastAPI no esta iniciado; el puerto 3000 esta libre." -ForegroundColor Yellow
    }
}

$mobile = Test-Endpoint -Uri $metroUrl
if ($null -ne $mobile) {
    Write-Host "[OK] Expo ya esta respondiendo en $metroUrl." -ForegroundColor Green
    $metroConnection = Get-NetTCPConnection -State Listen -LocalPort 8081 -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -ne $metroConnection) {
        $metroProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $($metroConnection.OwningProcess)" -ErrorAction SilentlyContinue
        if ($null -ne $metroProcess -and $metroProcess.CommandLine -notmatch "(^|\s)--go(\s|$)") {
            Write-Warning "Expo fue iniciado sin --go. Deten esa terminal con Ctrl+C y vuelve a ejecutar start-all.ps1 para obtener un QR de Expo Go."
        }
    }
}
else {
    $metroPortOwner = Get-NetTCPConnection -State Listen -LocalPort 8081 -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -ne $metroPortOwner) {
        throw "El puerto 8081 esta ocupado por el proceso $($metroPortOwner.OwningProcess), pero Metro no responde."
    }
    if ($CheckOnly) {
        Write-Host "[PENDIENTE] Expo no esta iniciado; el puerto 8081 esta libre." -ForegroundColor Yellow
    }
}

if ($CheckOnly) {
    Write-Host ""
    Write-Host "Diagnostico terminado. No se inicio ningun proceso." -ForegroundColor Cyan
    exit 0
}

$shell = (Get-Process -Id $PID).Path
if ([string]::IsNullOrWhiteSpace($shell)) { $shell = "powershell.exe" }

if ($null -eq $backend) {
    Write-Host "[INICIO] Abriendo FastAPI en una terminal nueva..." -ForegroundColor Yellow
    Start-Process -FilePath $shell -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-File", $backendScript) -WorkingDirectory $projectRoot -WindowStyle Normal | Out-Null
    $backend = Wait-Endpoint -Uri $healthUrl -Attempts 45
    if ($null -eq $backend) {
        throw "FastAPI no respondio despues de 45 segundos. Revisa la terminal del backend."
    }
    Write-Host "[OK] FastAPI esta listo." -ForegroundColor Green
}

if ($null -eq $mobile) {
    Write-Host "[INICIO] Abriendo Expo en una terminal nueva..." -ForegroundColor Yellow
    Start-Process -FilePath $shell -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-File", $mobileScript) -WorkingDirectory $projectRoot -WindowStyle Normal | Out-Null
}

Write-Host ""
Write-Host "Kirby quedo levantado:" -ForegroundColor Cyan
Write-Host "  API:     http://127.0.0.1:3000"
Write-Host "  Docs:    http://127.0.0.1:3000/docs"
Write-Host "  Health:  $healthUrl"
Write-Host ""
Write-Host "Expo mostrara el QR y la URL del telefono en su propia terminal."
Write-Host "Para detener todo, presiona Ctrl+C en las terminales de backend y cliente movil."
