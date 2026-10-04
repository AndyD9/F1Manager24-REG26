# Développement

Pour jouer, il suffit de la [dernière version](https://github.com/AndyD9/F1Manager24-REG26/releases/latest) (voir le [README](README.md)).
Cette page concerne le code source.

## Contenu

| Dossier | Rôle |
|---|---|
| `ue4ss/Reg2026` | Mod UE4SS (Lua) : zones Straight Mode, chargement de `Reg2026Patch.dll`, F7, mesures de chaque passage en zone dans `Mods/Reg2026/mesures.csv`. |
| `tools_native/` | `reg2026patch.cpp` (la DLL), outils de recherche (point d'arrêt matériel, désassemblage), test des caves (`test/cave_test.cpp`). `build.bat` compile avec Visual Studio 2022. |
| `ui_mod/UIGameface` | Interface : cases **STRAIGHT** / **OVERTAKE** à la place de la case DRS. |
| `scripts/` | Construction des paks (valeurs, textes FR, interface), extraction et analyse des données circuits. |
| `REGLEMENT_2026.md`, `GUIDE_PAK_2026.md`, `VALEURS_2026.md`, `ZONES_2026.md` | Règlement et correspondance avec le jeu, méthode, valeurs, zones. |

## Prérequis

- F1 Manager 2024 v1.11 avec [UE4SS](https://github.com/UE4SS-RE/RE-UE4SS) v3.0.1.
- Visual Studio 2022 (C++) pour la DLL.
- Python 3 avec `pycryptodome`, `capstone`, `pefile`.
- Pour reconstruire le pak de valeurs : [retoc](https://github.com/trumank/retoc), UAssetGUI dans `tools/`, et la clé AES
  du jeu dans la variable `F1M24_AES_KEY` ou dans un fichier `aes_key.txt` à la racine (non versionné).

## Construire

1. DLL : `tools_native/build.bat` → `ue4ss/Reg2026/Reg2026Patch.dll`.
2. Pak d'interface : `python scripts/build_ui.py --install`.
3. Pak de valeurs : `pwsh scripts/build_install.ps1`, jeu fermé (méthode : `GUIDE_PAK_2026.md`, valeurs : `scripts/patch_2026.py`).
4. Optionnel : textes FR, `python scripts/build_loc.py --install`.

## Release

Un seul zip qui reprend l'arborescence du jeu, à décompresser dans le dossier du jeu :

```
F1Manager24/Content/Paks/                      zzz_Reg2026_P.pak/.ucas/.utoc, zzz_Reg2026UI_P.pak
F1Manager24/Binaries/Win64/ue4ss/Mods/Reg2026/ enabled.txt, Reg2026Patch.dll, Scripts/
```

Ne jamais publier la clé AES ni les fichiers extraits du jeu (`extract/`, `build/`).
