# Extrait Lvl_<circuit>.umap des 24 circuits (format legacy) dans extract\tracks\legacy\
$ErrorActionPreference = 'Stop'
$root  = Split-Path $PSScriptRoot -Parent
$retoc = "$root\tools\retoc\retoc.exe"
$aes   = if ($env:F1M24_AES_KEY) { $env:F1M24_AES_KEY } else { (Get-Content (Join-Path $PSScriptRoot '..es_key.txt') -TotalCount 1).Trim() }
$paks  = 'F:\NewReg2026_paks_tmp'
$out   = "$root\extract\tracks"
$tracks = 'AlbertPark','Bahrain','Baku','Barcelona','CircuitOfTheAmericas','GillesVilleneuve','HermanosRodriguez',
          'Hungaroring','Imola','Interlagos','Jeddah','MarinaBay','Miami','Monaco','Monza','Qatar','RedBullRing',
          'Shanghai','Silverstone','SpaFrancorchamps','Suzuka','Vegas','YasMarina','Zandvoort'

New-Item -ItemType Directory -Force "$out\json" | Out-Null
foreach ($t in $tracks) {
    $legacy = "$out\legacy\F1Manager24\Content\Circuits\$t\Lvl_$t.umap"
    if (-not (Test-Path $legacy)) {
        & $retoc -a $aes to-legacy --no-shaders --no-script-objects -f "Circuits/$t/Lvl_$t.umap" $paks "$out\legacy" 2>&1 | Out-Null
    }
    # pas de conversion JSON : certains niveaux font des dizaines de Mo (scripts\track_binary.py lit le binaire)
    Write-Host ("{0,-22} umap={1}" -f $t, (Test-Path $legacy))
}
