# F1 Manager 2024 — Règlement 2026

Un mod pour **F1 Manager 2024** qui fait courir les voitures avec le règlement F1 2026 :
aéro active (Straight Mode) pour tout le monde, Overtake Mode, ERS à 350 kW et nouvelles valeurs d'aéro.
Les changements agissent sur la simulation elle-même, pas seulement sur l'affichage.

**[⬇ Télécharger la dernière version](https://github.com/AndyD9/F1Manager24-REG26/releases/latest)**

## Ce qui change en course

| | Règlement 2026 | Dans le jeu |
|---|---|---|
| **Straight Mode** | Ailerons ouverts dans les zones, pour toutes les voitures, à chaque tour | Toute la grille a l'aileron ouvert dans les zones, dès le 1er tour. Pas en cas de voiture de sécurité, de drapeau ou de pluie. |
| **Zones** | Désignées par la FIA | Nombre de zones annoncé par la FIA pour chaque circuit (Monza 4, Spa 5, Suzuka 2…) |
| **Overtake Mode** | À moins d'1 s de la voiture devant : 0,5 MJ d'énergie en plus | +12,5 % de batterie, que la voiture dépense aussitôt à pleine puissance électrique |
| **ERS** | 350 kW, environ 50 % de la puissance | Plus de puissance électrique, batterie vide en ~10 s de déploiement, recharge plus forte |
| **Aéro** | Appui −30 %, voitures plus légères | Un peu moins de vitesse en virage (surtout les rapides), moins d'air sale derrière une voiture |

Dans le bandeau de chaque pilote, la case DRS est remplacée par deux cases :

- **STRAIGHT** (vert) : l'aileron est ouvert.
- **OVERTAKE** (couleur ERS) : le pilote a passé la ligne à moins d'1 s de la voiture devant.

Le détail du règlement et de chaque réglage est dans [REGLEMENT_2026.md](REGLEMENT_2026.md).

## Ce qu'il faut

- **F1 Manager 2024** sur Steam, **version 1.11** (la dernière).
- **UE4SS v3.0.1** : outil qui permet de charger des mods dans le jeu. Il est peut-être déjà installé si tu as
  d'autres mods ; il y a alors un dossier `ue4ss` dans `F1Manager24\Binaries\Win64`.

### Installer UE4SS (si ce n'est pas déjà fait)

1. Télécharge `UE4SS_v3.0.1.zip` sur la [page de la version 3.0.1](https://github.com/UE4SS-RE/RE-UE4SS/releases/tag/v3.0.1).
2. Décompresse-le dans `F1Manager24\Binaries\Win64` (tu dois obtenir `Win64\dwmapi.dll` et `Win64\ue4ss\`).

## Installation

1. Ouvre le dossier du jeu : dans Steam, clic droit sur **F1 Manager 2024** → **Gérer** → **Parcourir les fichiers locaux**.
2. Télécharge `Reg2026_vX.Y.Z.zip` depuis la [dernière version](https://github.com/AndyD9/F1Manager24-REG26/releases/latest).
3. Décompresse-le **dans ce dossier** (celui qui contient `F1Manager24`) et accepte de fusionner les dossiers.

C'est tout. Le zip contient déjà la bonne arborescence :

```
F1Manager24\Content\Paks\                       zzz_Reg2026_P (.pak/.ucas/.utoc), zzz_Reg2026UI_P.pak
F1Manager24\Binaries\Win64\ue4ss\Mods\Reg2026\  le mod (scripts et Reg2026Patch.dll)
```

### Vérifier que ça marche

- En course, les cases **STRAIGHT** / **OVERTAKE** apparaissent dans le bandeau des pilotes, à la place de DRS.
- Le fichier `F1Manager24\Binaries\Win64\ue4ss\Mods\Reg2026\patch.log` contient la ligne
  « Straight Mode actif dès le 1er tour… ».

## En jeu

- **F7** : passe du règlement 2026 à la règle d'origine du jeu (DRS à moins d'1 s, après 2 tours), et inversement.
  Un message s'affiche à l'écran. Les valeurs ERS et aéro restent celles de 2026.

## Mise à jour

Décompresse le zip de la nouvelle version au même endroit, en remplaçant les fichiers.

## Désinstallation

Supprime :

- dans `F1Manager24\Content\Paks` : `zzz_Reg2026_P.pak`, `zzz_Reg2026_P.ucas`, `zzz_Reg2026_P.utoc` et `zzz_Reg2026UI_P.pak` ;
- le dossier `F1Manager24\Binaries\Win64\ue4ss\Mods\Reg2026`.

Le mod ne modifie ni les fichiers d'origine du jeu ni tes sauvegardes : une fois ces fichiers supprimés, tout redevient normal.

## Problèmes

| Problème | Solution |
|---|---|
| Le jeu plante au lancement ou en course | Supprime `Mods\Reg2026\Reg2026Patch.dll` (le reste du mod continue de marcher) et [ouvre un ticket](https://github.com/AndyD9/F1Manager24-REG26/issues) avec `patch.log` et `ue4ss\UE4SS.log`. |
| Pas de cases STRAIGHT / OVERTAKE | Vérifie que `zzz_Reg2026UI_P.pak` est bien dans `Content\Paks`. Un autre mod qui modifie le bandeau des pilotes peut entrer en conflit. |
| `patch.log` dit « ce n'est pas F1 Manager 2024 v1.11 » ou « octets inattendus » | Ta version du jeu n'est pas la 1.11 : la partie Straight Mode / Overtake ne s'active pas, par sécurité. |
| Rien ne se passe du tout | UE4SS n'est pas installé ou pas dans le bon dossier (voir plus haut). |
| Conflit avec un autre mod | Les mods qui modifient les données de course (ERS, aéro, dépassements) ou l'interface du bandeau pilote peuvent se gêner. |

## À savoir

- `Reg2026Patch.dll` modifie le jeu **en mémoire uniquement**, à chaque lancement.
- Mod de fans, non affilié à Frontier Developments ni à la Formula 1. Les paks contiennent quelques fichiers
  de données du jeu modifiés ; il faut posséder le jeu pour les utiliser.
- Code source et outils : [DEVELOPPEMENT.md](DEVELOPPEMENT.md). Licence [MIT](LICENSE).
