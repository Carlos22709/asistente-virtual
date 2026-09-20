# Inicia Expo Go y prioriza la IP privada de Tailscale cuando esta disponible.

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$npxCommand = Get-Command npx.exe, npx.cmd -ErrorAction SilentlyContinue |
    Select-Object -First 1

if (-not $npxCommand) {
    throw "No se encontró npx en PATH. Comprueba la instalación global de Node.js."
}

$nodeDirectory = Split-Path -Parent $npxCommand.Source
$env:Path = "$nodeDirectory;$env:Path"
$tailscalePath = "C:\Program Files\Tailscale\tailscale.exe"
if (Test-Path -LiteralPath $tailscalePath) {
    $tailscaleStatusText = & $tailscalePath status --json 2>$null
    if ($LASTEXITCODE -eq 0) {
        $tailscaleStatus = $tailscaleStatusText | ConvertFrom-Json
        $tailscaleIp = @($tailscaleStatus.TailscaleIPs | Where-Object { $_ -match '^100\.' })[0]
        if ($tailscaleStatus.BackendState -eq "Running" -and $tailscaleIp) {
            $tailscaleIp = $tailscaleIp.Trim()
            $env:EXPO_PUBLIC_API_URL = "http://${tailscaleIp}:3000"
            $env:REACT_NATIVE_PACKAGER_HOSTNAME = $tailscaleIp
            Write-Host "Expo usará Tailscale para API y Metro: $tailscaleIp"
        }
    }
}

Set-Location (Join-Path $projectRoot "mobile")
& $npxCommand.Source expo start --go --lan
