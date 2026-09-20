# Muestra, copia o prueba la URL y el token del webhook bancario.

[CmdletBinding()]
param(
    [ValidateSet("None", "Token", "Url")]
    [string]$Copy = "None",
    [switch]$Test
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $projectRoot "backend\.env"

if (-not (Test-Path -LiteralPath $envPath)) {
    throw "No existe backend/.env. Configura primero el backend."
}

$tokenLine = Get-Content -LiteralPath $envPath -Encoding utf8 |
    Where-Object { $_ -match '^BANK_WEBHOOK_TOKEN=' } |
    Select-Object -First 1
if (-not $tokenLine) {
    throw "BANK_WEBHOOK_TOKEN no está configurado en backend/.env."
}

$token = $tokenLine.Substring("BANK_WEBHOOK_TOKEN=".Length).Trim()
if ($token.Length -lt 24) {
    throw "BANK_WEBHOOK_TOKEN debe tener al menos 24 caracteres."
}

$tailscalePath = @(
    (Get-Command tailscale.exe -ErrorAction SilentlyContinue).Source
    "C:\Program Files\Tailscale\tailscale.exe"
) | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -First 1

$ipAddress = $null
$networkName = "red local"
if ($tailscalePath) {
    $tailscaleStatusText = & $tailscalePath status --json 2>$null
    if ($LASTEXITCODE -eq 0) {
        $tailscaleStatus = $tailscaleStatusText | ConvertFrom-Json
        $tailscaleIp = @($tailscaleStatus.TailscaleIPs | Where-Object { $_ -match '^100\.' })[0]
        if ($tailscaleStatus.BackendState -eq "Running" -and $tailscaleIp) {
            $ipAddress = $tailscaleIp.Trim()
            $networkName = "Tailscale"
        }
    }
}

if (-not $ipAddress) {
    $network = Get-NetIPConfiguration |
        Where-Object { $_.IPv4DefaultGateway -and $_.NetAdapter.Status -eq "Up" } |
        Select-Object -First 1
    $ipAddress = @($network.IPv4Address)[0].IPAddress
}
if (-not $ipAddress) {
    throw "No se encontró una IPv4 activa. Conecta Tailscale o la red local."
}

$webhookUrl = "http://${ipAddress}:3000/webhooks/bank-transactions"
$statusUrl = "$webhookUrl/status"

Write-Host "URL para iPhone/Android: $webhookUrl"
Write-Host "Red seleccionada: $networkName"
Write-Host "La clave permanece oculta. Usa -Copy Token para copiarla."

if ($Copy -eq "Token") {
    Set-Clipboard -Value $token
    Write-Host "Clave copiada al portapapeles. Pégala en X-Webhook-Token y limpia el portapapeles después."
} elseif ($Copy -eq "Url") {
    Set-Clipboard -Value $webhookUrl
    Write-Host "URL copiada al portapapeles."
}

if ($Test) {
    try {
        $response = Invoke-RestMethod `
            -Method Get `
            -Uri $statusUrl `
            -Headers @{ "X-Webhook-Token" = $token } `
            -TimeoutSec 8
        Write-Host "Conexión correcta. Estado: $($response.status); modelo: $($response.model)."
    } catch {
        throw "No fue posible validar el webhook. Inicia el backend y revisa red/firewall. $($_.Exception.Message)"
    }
}
