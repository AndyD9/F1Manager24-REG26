# F1 Manager 24 — Règlement 2026

Mod pour **F1 Manager 2024** (Steam) qui adapte les courses au règlement technique 2026 :
Straight Mode (aéro active), Overtake Mode et ERS 350 kW.

## État actuel

| Partie | Effet en course |
|---|---|
| **Straight Mode** pour toute la grille, dès le 1er tour — `Reg2026Patch.dll` | **Réel** : le jeu ouvre lui-même le DRS de toutes les voitures dans les zones, avec son vrai gain de vitesse. Blocages gardés : voiture de sécurité, drapeaux, pluie. |
| **Overtake Mode** — `Reg2026Patch.dll` | **Réel** : à moins d'1 s au point de détection, +12,5 % de batterie ERS (0,5 MJ sur 4 MJ), une fois par tour. |
| Zones Straight Mode — `ue4ss/Reg2026` | Zones du jeu + zones ajoutées au nombre annoncé par la FIA (ZONES_2026.md). |
| Cases STRAIGHT / OVERTAKE — `ui_mod` | Interface : bandeau de chaque pilote, au style du jeu. |
| Valeurs 2026 (ERS, aéro, air sale) — pak `zzz_Reg2026_P` | **Réel**. À construire soi-même (voir `GUIDE_PAK_2026.md`), non distribué car il contient des données du jeu. |

**F7** : règlement 2026 ou règle d'origine du jeu (DRS à moins d'1 s). Journal du patch : `Mods/Reg2026/patch.log`.
Le patch vise **F1 Manager 2024 v1.11** : sur une autre version, il ne modifie rien et l'écrit dans le journal.
Détails et sources : [REGLEMENT_2026.md](REGLEMENT_2026.md).

## Contenu

| Dossier | Rôle |
|---|---|
| `ue4ss/Reg2026` | Mod UE4SS (Lua) : zones Straight Mode, chargement de `Reg2026Patch.dll`, F7, mesures de chaque passage en zone dans `Mods/Reg2026/mesures.csv`. |
| `tools_native/` | `reg2026patch.cpp` (la DLL), outils de recherche (point d'arrêt matériel, désassemblage). `build.bat` compile avec Visual Studio 2022. |
| `ui_mod/UIGameface` | Interface : cases **STRAIGHT** / **OVERTAKE** à la place de la case DRS. |
| `scripts/` | Construction des paks (valeurs, textes FR, interface), extraction et analyse des données circuits. |
| `REGLEMENT_2026.md`, `GUIDE_PAK_2026.md`, `VALEURS_2026.md`, `ZONES_2026.md` | Règlement et correspondance avec le jeu, méthode, valeurs, zones. |

## Prérequis

- F1 Manager 2024 avec [UE4SS](https://github.com/UE4SS-RE/RE-UE4SS).
- Python 3 avec `pycryptodome`.
- Pour reconstruire les paks de données : [retoc](https://github.com/trumank/retoc), et la clé AES du jeu
  dans la variable `F1M24_AES_KEY` ou dans un fichier `aes_key.txt` à la racine (non versionné).

## Installation rapide

Télécharger la dernière [release](https://github.com/AndyD9/F1Manager24-REG26/releases/latest) :

- `Reg2026_UE4SS.zip` → dézipper dans `F1Manager24/Binaries/Win64/ue4ss/Mods/` (contient `Reg2026Patch.dll`)
- `zzz_Reg2026UI_P.pak` → copier dans `F1Manager24/Content/Paks/`

## Installation depuis les sources

1. Compiler la DLL (`tools_native/build.bat`, Visual Studio 2022), puis copier `ue4ss/Reg2026` dans
   `F1Manager24/Binaries/Win64/ue4ss/Mods/` (avec `enabled.txt` et `Reg2026Patch.dll`).
2. Construire et installer le pak d'interface :
   ```
   python scripts/build_ui.py --install
   ```
3. Optionnel : textes FR (`scripts/build_loc.py --install`) et valeurs 2026 (voir `GUIDE_PAK_2026.md`).

## Avertissement

Projet de fans, non affilié à Frontier Developments ni à la Formula 1. Aucun fichier du jeu n'est
distribué ici : les paks se construisent localement à partir de votre propre copie du jeu.

## Licence

[MIT](LICENSE)
