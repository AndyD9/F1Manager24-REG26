# Reconstruit et installe le mod zzz_Reg2026_P.
# Usage : pwsh scripts\build_install.ps1   (le jeu doit être fermé)
#
# Étapes : patch des valeurs (JSON) -> .uasset/.uexp via UAssetGUI -> build_raw.py
# (en-têtes et index d'origine du jeu, seules les données changent) -> copie dans Paks.
# Ne pas utiliser « retoc to-zen » seul : ses en-têtes ne correspondent pas au moteur du jeu (plantage).
$ErrorActionPreference = 'Stop'
$root  = Split-Path $PSScriptRoot -Parent
$tools = "$root\tools"
$paks  = 'F:\SteamLibrary\steamapps\common\F1 Manager 2024\F1Manager24\Content\Paks'
$stage = "$root\build\mod"

# Asset -> dossier dans Content
$assets = @{
    RaceSimDataAsset          = 'RaceSim'
    DriverTacticsDataAsset    = 'RaceSim'
    DRSAccelerationSpeedCurce = 'RaceSim'
    RaceSimAIDataAsset        = 'RaceSim\AI'
    CarStatsDataAsset         = 'SharedAssets\DataAssets'
}

if (Get-Process F1Manager24 -ErrorAction SilentlyContinue) { throw 'Ferme le jeu avant.' }

python "$root\scripts\patch_2026.py"

if (Test-Path $stage) { Remove-Item -LiteralPath $stage -Recurse -Force }
foreach ($n in $assets.Keys) {
    $d = "$stage\F1Manager24\Content\$($assets[$n])"
    New-Item -ItemType Directory -Force $d | Out-Null
    Start-Process "$tools\UAssetGUI.exe" -ArgumentList "fromjson `"$root\build\json\$n.json`" `"$d\$n.uasset`" F1M24" -Wait -NoNewWindow
}

python "$root\scripts\build_raw.py"

Copy-Item "$root\build\out\zzz_Reg2026_P.*" $paks -Force
Write-Host "Installé dans $paks"
