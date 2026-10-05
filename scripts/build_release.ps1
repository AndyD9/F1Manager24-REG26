# Construit le zip d'une version, Reg2026_vX.Y.Z.zip, à décompresser dans le dossier du jeu. Un seul zip depuis la
# v0.4.1, super clipping actif (actif=1) : le déploiement pour le chrono est calé avec la recharge en bout de ligne
# droite (sans elle, la grille vide ses batteries et passe en RÉSERVE) ; F6 la coupe en jeu.
# Les paks viennent de build\out (scripts\build_install.ps1 et scripts\build_ui.py), la DLL et les scripts de ue4ss\Reg2026
# (tools_native\build.bat). Usage : .\scripts\build_release.ps1 0.4.1
param([Parameter(Mandatory = $true)][string] $Version)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$out = "$root\build\out"
$mod = "$root\ue4ss\Reg2026"
$release = "$root\build\release"

$paks = @('zzz_Reg2026_P.pak', 'zzz_Reg2026_P.ucas', 'zzz_Reg2026_P.utoc', 'zzz_Reg2026UI_P.pak')
$modFiles = @('enabled.txt', 'Reg2026Patch.dll', 'Scripts\main.lua', 'Scripts\zones.lua')
foreach ($f in $paks) { if (-not (Test-Path "$out\$f")) { throw "manque $out\$f" } }
foreach ($f in $modFiles) { if (-not (Test-Path "$mod\$f")) { throw "manque $mod\$f" } }

$clip = "vitesse_max=290`nvitesse_max_overtake=337`nrecharge=0.002`novertake_vitesse_min=250`novertake_distance=2000`novertake_ecart_attaque=0.6`novertake_batterie=1`novertake_batterie_max=0.20`ndeploiement_boost=0.40`ndeploiement_equilibre=0.60`n"
foreach ($variant in @(@{ suffix = ''; actif = 1 })) {
    $name = "Reg2026_v$Version$($variant.suffix)"
    $dir = "$release\v$Version\$name"
    if (Test-Path $dir) { Remove-Item -LiteralPath $dir -Recurse -Force }
    $pakDir = "$dir\F1Manager24\Content\Paks"
    $modDir = "$dir\F1Manager24\Binaries\Win64\ue4ss\Mods\Reg2026"
    New-Item -ItemType Directory -Force $pakDir, "$modDir\Scripts" | Out-Null
    foreach ($f in $paks) { Copy-Item "$out\$f" $pakDir }
    foreach ($f in $modFiles) { Copy-Item "$mod\$f" "$modDir\$f" }
    [IO.File]::WriteAllText("$modDir\superclipping.ini", "actif=$($variant.actif)`n$clip")
    $zip = "$release\$name.zip"
    if (Test-Path $zip) { Remove-Item -LiteralPath $zip -Force }
    Compress-Archive -Path "$dir\F1Manager24" -DestinationPath $zip
    Write-Host "$zip ($([math]::Round((Get-Item $zip).Length / 1KB)) Ko)"
}
