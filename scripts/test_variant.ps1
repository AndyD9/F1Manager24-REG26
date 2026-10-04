# Installe une variante du mod, lance le jeu et indique s'il plante au démarrage.
# Usage : pwsh scripts\test_variant.ps1 -Name <variante>   (cherche build\variants\<variante>\zzz_Reg2026_P.*)
param([Parameter(Mandatory)] [string] $Name, [int] $WaitSeconds = 60)
$ErrorActionPreference = 'Stop'
$root    = Split-Path $PSScriptRoot -Parent
$paks    = 'F:\SteamLibrary\steamapps\common\F1 Manager 2024\F1Manager24\Content\Paks'
$crashes = "$env:LOCALAPPDATA\F1Manager24\Saved\Crashes"

if (Get-Process F1Manager24 -ErrorAction SilentlyContinue) { throw 'Le jeu tourne déjà.' }

Remove-Item "$paks\zzz_Reg2026_P.*" -ErrorAction SilentlyContinue
if ($Name -ne 'none') { Copy-Item "$root\build\variants\$Name\zzz_Reg2026_P.*" $paks -Force }

$before = @(Get-ChildItem $crashes -Directory -ErrorAction SilentlyContinue | % Name)
Start-Process 'steam://rungameid/2591280'

$result = 'OK'
for ($i = 0; $i -lt $WaitSeconds; $i += 2) {
    Start-Sleep -Seconds 2
    $new = @(Get-ChildItem $crashes -Directory -ErrorAction SilentlyContinue | % Name | ? { $_ -notin $before })
    if ($new.Count -gt 0) { $result = "CRASH ($($new -join ', '))"; break }
}

Get-Process F1Manager24, CrashReportClient -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 3
Remove-Item "$paks\zzz_Reg2026_P.*" -ErrorAction SilentlyContinue
Write-Host "$Name : $result"
