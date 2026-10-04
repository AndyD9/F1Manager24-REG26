# Construit des variantes du mod pour isoler un plantage.
# A_orig_retoc : fichiers d'origine non modifiés (teste retoc seul)
# B_<Asset>    : un seul fichier modifié
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$retoc = "$root\tools\retoc\retoc.exe"
$assets = @{
    RaceSimDataAsset          = 'RaceSim'
    DriverTacticsDataAsset    = 'RaceSim'
    DRSAccelerationSpeedCurce = 'RaceSim'
    RaceSimAIDataAsset        = 'RaceSim\AI'
    CarStatsDataAsset         = 'SharedAssets\DataAssets'
}

function Build-Variant([string] $Name, [string] $SourceRoot, [string[]] $Names) {
    $src = Join-Path $root "build\variants\$Name\src"
    if (Test-Path $src) { Remove-Item -LiteralPath $src -Recurse -Force }
    foreach ($n in $Names) {
        $rel = "F1Manager24\Content\$($assets[$n])"
        New-Item -ItemType Directory -Force (Join-Path $src $rel) | Out-Null
        foreach ($ext in 'uasset', 'uexp') {
            Copy-Item (Join-Path $SourceRoot "$rel\$n.$ext") (Join-Path $src $rel)
        }
    }
    & $retoc to-zen --version UE5_1 $src (Join-Path $root "build\variants\$Name\zzz_Reg2026_P.utoc") 2>&1 | Select-Object -Last 1
}

Build-Variant 'A_orig_retoc' "$root\extract\legacy" $assets.Keys
foreach ($n in $assets.Keys) { Build-Variant "B_$n" "$root\build\mod" @($n) }
Get-ChildItem "$root\build\variants" -Directory | ForEach-Object Name
