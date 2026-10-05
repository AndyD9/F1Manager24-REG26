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
| **Overtake Mode** | À moins d'1 s de la voiture devant : 0,5 MJ d'énergie en plus | 12,5 % d'énergie en plus de la batterie, gardés jusqu'à une vraie occasion (voiture devant à moins de 0,6 s, au plus jusqu'à la fin du tour suivant). Alors : pleine puissance électrique jusqu'à 337 km/h (les autres s'arrêtent à 290), payée par le crédit puis par la batterie (20 % au plus), jusqu'au freinage, et l'avantage au dépassement que le jeu réservait au DRS (2 km après chaque détection). Jauge OVERTAKE au-dessus du bandeau de chaque pilote : crédit restant sur 0,50 MJ, allumée pendant l'utilisation. Notification « Overtake Mode activé » quand il devient disponible (2 tours après le départ ou une relance) |
| **ERS** | 350 kW, environ 50 % de la puissance, 8,5 MJ récupérés par tour | Batterie vide en ~10 s de déploiement, recharge de 350 kW au freinage et de 250 kW en bout de ligne droite (super clipping). Les pilotes déploient à fond en accélération pour le chrono (stratégies Boost et Équilibré). Mesuré à Monza : 1:26.0 de médiane, 1:22.9 au meilleur tour (vrai GP 2026 : 1:23.5) |
| **Aéro** | Appui −30 %, voitures plus légères | Un peu moins de vitesse en virage (surtout les rapides), moins d'air sale derrière une voiture |
| **Gestion de l'énergie** | Boost manuel, récupération au lever de pied, « clipping » en bout de ligne droite | Les quatre stratégies ERS deviennent **Boost**, **Équilibré**, **Réserve** et **Lift & Coast** (voir plus bas) |

Dans le bandeau de chaque pilote, la case DRS est remplacée par deux cases :

- **STRAIGHT** (vert) : l'aileron est ouvert.
- **OVERTAKE** (couleur ERS) : le pilote a passé la ligne à moins d'1 s de la voiture devant.

Au-dessus du nom du pilote, une ligne affiche la **vitesse**, la **batterie** et l'état de l'**ERS** (déploie, recharge, neutre).

### Stratégies ERS

Dans l'écran Stratégies ERS, les quatre réglages du jeu sont renommés et deux d'entre eux changent de comportement :

| Stratégie 2026 | Réglage d'origine | Comportement |
|---|---|---|
| **Boost** | Déploiement | Le pilote déploie à fond en accélération (sous 290 km/h) tant que sa batterie est au-dessus de 40 %, pour le chrono. C'est la stratégie de course de l'IA. |
| **Équilibré** | Neutre | Pareil, mais seulement au-dessus de 60 % de batterie. |
| **Réserve** | Top-Up | Le pilote garde son énergie : pas de déploiement, sauf en Overtake Mode ou en bataille (une voiture à moins d'1 s devant ou derrière). |
| **Lift & Coast** | Récupération | Plus d'électrique au-delà de 250 km/h et recharge au-dessus : la batterie se remplit en bout de ligne droite. |

### Super clipping

En 2026, la puissance électrique est réduite à haute vitesse : plus personne ne déploie au-delà de 290 km/h, sauf une
voiture en Overtake Mode (jusqu'à 337 km/h). C'est ce qui donne à l'Overtake Mode son avantage en vitesse de pointe.
Au-delà de la limite, à fond, la batterie se recharge (250 kW, le super clipping) : c'est elle qui paie le déploiement
de la ligne droite suivante. **F6** en jeu coupe ou remet cette recharge (la limite de vitesse reste) ; sans elle, les
batteries se vident et l'IA passe en Réserve.

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
- **F6** : active ou coupe le super clipping, c'est-à-dire la recharge en bout de ligne droite (voir plus haut). Le réglage est gardé d'une partie à l'autre
  (`Mods\Reg2026\superclipping.ini`).

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
| Un autre mod change les mêmes données de course | Les mods qui remplacent les fichiers de données de course (par exemple **RRacingV5**) passent devant le pak du mod, et ses valeurs ERS / aéro ne sont alors jamais lues. Le mod les réécrit en mémoire au chargement de chaque course (`patch.log` : « valeurs 2026 » dans `ue4ss\UE4SS.log`, « tableaux aéro 2026 » dans `patch.log`), mais le reste des réglages de l'autre mod s'applique aussi : le résultat est un mélange des deux. Pour le règlement 2026 tel qu'il a été réglé, désactive l'autre mod. |
| Un autre mod change le bandeau des pilotes | Les deux interfaces se gênent : garde l'un ou l'autre. |

## À savoir

- `Reg2026Patch.dll` modifie le jeu **en mémoire uniquement**, à chaque lancement.
- Mod de fans, non affilié à Frontier Developments ni à la Formula 1. Les paks contiennent quelques fichiers
  de données du jeu modifiés ; il faut posséder le jeu pour les utiliser.
- Code source et outils : [DEVELOPPEMENT.md](DEVELOPPEMENT.md). Licence [MIT](LICENSE).
