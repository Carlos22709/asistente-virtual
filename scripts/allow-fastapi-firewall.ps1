# Autoriza el puerto privado de FastAPI en el Firewall de Windows.

$ErrorActionPreference = "Stop"
$ruleName = "Kirby Assistant FastAPI"
$existing = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue

if ($existing) {
    Set-NetFirewallRule -DisplayName $ruleName -Enabled True -Direction Inbound -Action Allow -Profile Any
    Set-NetFirewallAddressFilter -AssociatedNetFirewallRule $existing -RemoteAddress LocalSubnet
    $existing | Get-NetFirewallPortFilter | Set-NetFirewallPortFilter -Protocol TCP -LocalPort 3000
} else {
    New-NetFirewallRule `
        -DisplayName $ruleName `
        -Description "Permite que Kirby Assistant consulte FastAPI únicamente desde la red local." `
        -Direction Inbound `
        -Action Allow `
        -Protocol TCP `
        -LocalPort 3000 `
        -Profile Any `
        -RemoteAddress LocalSubnet | Out-Null
}
