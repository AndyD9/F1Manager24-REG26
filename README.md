# F1 Manager 24 — Règlement 2026

Mod pour **F1 Manager 2024** (Steam) qui adapte les courses au règlement technique 2026 :
Straight Mode (aéro active), Overtake Mode et ERS 350 kW.

## Contenu

| Dossier | Rôle |
|---|---|
| `ue4ss/Reg2026` | Mod UE4SS (Lua) : ajoute les zones Straight Mode à chaque circuit et force l'état « aéro ouverte » dans ces zones (F7 pour activer/couper). |
| `ui_mod/UIGameface` | Interface : remplace la case DRS du bandeau de chaque pilote par deux cases **STRAIGHT** / **OVERTAKE**, au style du jeu. |
| `scripts/` | Construction des paks (valeurs, textes FR, interface), extraction et analyse des données circuits. |
| `GUIDE_PAK_2026.md`, `VALEURS_2026.md`, `ZONES_2026.md` | Notes techniques : méthode, valeurs modifiées, zones ajoutées. |

## Prérequis

- F1 Manager 2024 avec [UE4SS](https://github.com/UE4SS-RE/RE-UE4SS).
- Python 3 avec `pycryptodome`.
- Pour reconstruire les paks de données : [retoc](https://github.com/trumank/retoc), et la clé AES du jeu
  dans la variable `F1M24_AES_KEY` ou dans un fichier `aes_key.txt` à la racine (non versionné).

## Installation rapide

Télécharger la dernière [release](https://github.com/AndyD9/F1Manager24-REG26/releases/latest) :

- `Reg2026_UE4SS.zip` → dézipper dans `F1Manager24/Binaries/Win64/ue4ss/Mods/`
- `zzz_Reg2026UI_P.pak` → copier dans `F1Manager24/Content/Paks/`

## Installation depuis les sources

1. Copier `ue4ss/Reg2026` dans `F1Manager24/Binaries/Win64/ue4ss/Mods/` (avec `enabled.txt`).
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
