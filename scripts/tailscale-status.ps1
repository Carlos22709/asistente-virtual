# Comprueba Tailscale, el dispositivo movil y opcionalmente la API.

[CmdletBinding()]
param(
    [switch]$TestBackend
)

$ErrorActionPreference = "Stop"
$tailscalePath = "C:\Program Files\Tailscale\tailscale.exe"

if (-not (Test-Path -LiteralPath $tailscalePath)) {
    throw "Tailscale no está instalado en este computador."
}

$statusText = & $tailscalePath status --json
if ($LASTEXITCODE -ne 0) {
    throw "No fue posible consultar Tailscale."
}
$status = $statusText | ConvertFrom-Json

if ($status.BackendState -ne "Running") {
    throw "Tailscale requiere inicio de sesión. Abre su icono en la bandeja y selecciona Log in."
}

$selfIp = @($status.TailscaleIPs | Where-Object { $_ -match '^100\.' })[0]
if (-not $selfIp) {
    throw "Tailscale está activo, pero no asignó una IPv4."
}

Write-Host "Tailscale conectado."
Write-Host "Computador: $($status.Self.HostName)"
Write-Host "IPv4 privada: $selfIp"
Write-Host "API: http://${selfIp}:3000"

$peers = @()
if ($status.Peer) {
    $peers = @($status.Peer.PSObject.Properties.Value)
}
$iosPeers = @($peers | Where-Object { $_.OS -eq "iOS" })
if ($iosPeers.Count -eq 0) {
    Write-Host "iPhone: todavía no aparece en esta tailnet."
} else {
    foreach ($peer in $iosPeers) {
        $state = if ($peer.Online) { "en línea" } else { "fuera de línea" }
        $peerName = $peer.HostName
        if ($peerName -eq "localhost" -and $peer.DNSName) {
            $peerName = $peer.DNSName.Split('.')[0]
        }
        Write-Host "iPhone: $peerName ($state)"
    }
}

if ($TestBackend) {
    try {
        $health = Invoke-RestMethod -Uri "http://${selfIp}:3000/health" -TimeoutSec 8
        Write-Host "Backend accesible por Tailscale: $($health.status)"
    } catch {
        throw "Tailscale funciona, pero el backend no responde en el puerto 3000. Inicia scripts/start-backend.ps1."
    }
}
