# Règlement F1 2026 → F1 Manager 2024

Ce que dit le règlement 2026, ce que le mod fait déjà, et comment s'en approcher avec ce qu'on sait modifier
(données du pak, Lua UE4SS, patch natif `Reg2026Patch.dll`).

Sources : [Motor Sport Magazine](https://www.motorsportmagazine.com/articles/single-seaters/f1/explained-active-aero-overtake-mode-and-the-new-f1-2026-terminology/),
[The Race](https://www.the-race.com/formula-1/boost-overtake-mode-active-aero-recharge-key-2026-terms-explained/),
[ESPN](https://www.espn.com/racing/f1/story/_/id/48090668/2026-f1-rules-whats-new-cars-how-changes-affect-racing),
[Formula1.com](https://www.formula1.com/en/latest/article/2026-regulations-explained-all-you-need-to-know-about-f1s-new-power-units.14jfv7a36905uDJDdNyfQd),
[Motorsport Week](https://www.motorsportweek.com/2026/02/17/what-is-drs-in-f1-and-how-does-it-work-and-what-changes-in-2026/).

## 1. Le règlement en bref

| Élément | 2026 |
|---|---|
| **Straight Mode** | Ailerons avant **et** arrière ouverts dans des zones désignées par la FIA (panneaux « SM »). **Toutes les voitures, à chaque tour**, sans condition d'écart. Corner Mode (appui maximal) partout ailleurs. |
| Straight Mode sous la pluie | Mode partiel : aileron avant seulement, zones raccourcies. |
| Straight Mode sous voiture de sécurité | Proposition FIA : autorisé si la piste est sèche. |
| **Overtake Mode** | À **moins d'1 s** de la voiture devant au point de détection (en principe le dernier virage) : **+0,5 MJ** d'énergie électrique à utiliser **au tour suivant**, où le pilote veut. Pleine puissance de 350 kW **jusqu'à 337 km/h** (sinon la puissance électrique baisse dès 290 km/h et tombe à 0 à 355 km/h). |
| **Boost** | Bouton de déploiement manuel, partout, selon la charge de la batterie. |
| Moteur | V6 1,6 L turbo, MGU-H supprimé, MGU-K **350 kW** (120 kW avant) : environ **50 % électrique**. |
| Énergie | Batterie **4 MJ** au maximum, récupération jusqu'à **8,5 MJ par tour** (freinage, mi-gaz, « clipping » en bout de ligne droite à 250 kW au maximum, lever de pied). |
| Voiture | **770 kg** (−30 kg), empattement −20 cm, largeur −10 cm, appui **−30 %**, traînée **−55 %** en Straight Mode, pneus plus étroits (−25 mm à l'avant, −30 mm à l'arrière), 90 % de l'appui conservé à 20 m derrière une voiture. |

## 2. Ce que le jeu permet de modifier

| Levier | Où | Effet |
|---|---|---|
| Valeurs de simulation | pak `zzz_Reg2026_P` (RaceSimDataAsset, CarStatsDataAsset, courbe DRS…) | Réel, global, fixé au chargement |
| Zones DRS | Lua : tableaux `m_DRSZoneStart` / `m_DRSZoneEnd` du circuit | Réel (début et fin seulement, **jamais** de point de détection : drapeau rouge) |
| Machine à états DRS | `Reg2026Patch.dll`, fonction exe+0x230C2B0 | Réel : décide qui a le DRS, quand il s'ouvre et se ferme |
| Objet voiture de la simulation | 0x10D8 octets par voiture ; DRS en +0x86D | Réel, voiture par voiture, depuis la DLL |
| Données affichées (CarData) | Lua | Visuel seulement (recopié depuis la simulation à chaque image) |

## 3. Correspondance et état

| Règle 2026 | Dans le mod | État |
|---|---|---|
| Straight Mode pour tous, sans écart | Patch : suppression du test « > 1 s » au point de détection | ✅ fait, mesuré à Monza (toute la grille au niveau « avec DRS ») |
| Zones Straight Mode désignées | Zones DRS du jeu + 26 zones ajoutées (ZONES_2026.md), enchaînées par le jeu | ✅ fait ; à aligner sur les zones FIA officielles circuit par circuit |
| Dès le 1er tour | Patch de la condition de tour (exe+0x230C335, objet voiture +0x870) | 🧪 codé, à tester en course |
| Sous voiture de sécurité (si sec) | Le jeu bloque | ➖ garder le blocage : aucun effet utile à vitesse de safety car |
| Pluie : mode partiel | Le jeu bloque complètement sur piste mouillée | ➖ approximation acceptable ; option : autoriser avec un gain réduit |
| Gain du Straight Mode | Courbe `DRSAccelerationSpeedCurce` (réduite à 0,75 dans le pak), `DRSTopSpeedMultiplier` | 🔧 remettre 1,0 au moins : en 2026 l'ouverture est plus large (avant + arrière) |
| **Overtake Mode** (< 1 s → +0,5 MJ au tour suivant) | Code ajouté à la place du test d'1 s : à moins d'1 s, +12,5 % de batterie (objet voiture +0x878, 0..1), une fois par tour | 🧪 codé, à tester en course |
| Case OVERTAKE du bandeau | S'allume pour tout le monde depuis le patch | 🔧 la relier au vrai Overtake Mode (DLL → fichier lu par le Lua → interface) |
| 350 kW, 50 % électrique | Pak : `ERSAccelDeployBatteryRate` −0,10, `ERSAccelerationMultiplier_Inactive` 0,55 | ✅ cohérent : −0,10/s vide la batterie en ~10 s, et 4 MJ à 350 kW durent 11,4 s |
| 8,5 MJ récupérés par tour | Pak : `ERSBrakingChargeBatteryRate` 0,12 | ✅ ordre de grandeur correct (~2 batteries par tour) |
| Puissance électrique réduite au-delà de 290 km/h | Aucun équivalent direct (le jeu applique un multiplicateur d'accélération) | 🔍 à étudier : courbe d'accélération ERS selon la vitesse, si elle existe |
| Appui −30 %, traînée −55 % | CarStats : `AeroSpeedMultipliers`, `TopSpeed`, `Acceleration` | 🔧 vitesse en virage plus basse, vitesse de pointe plus haute |
| 770 kg, pneus étroits | CarStats `MassWeight`, données pneus | 🔍 à étudier (moins d'adhérence, usure) |
| Moins d'air sale (90 % d'appui à 20 m) | Pak : `DirtyAirMaxDist` 150 (220 avant) | ✅ fait ; `DirtyAirSpeedMultipliers` à ajuster |
| Boost manuel | Modes ERS du jeu (déploiement) | ✅ existe déjà dans le jeu |

## 4. Ordre proposé

1. **Straight Mode dès le 1er tour** : patch de la condition de tour dans exe+0x230C2B0. Petit, même méthode que le patch actuel.
2. **Overtake Mode réel** : petit bout de code natif à la place du test d'1 s. À moins d'1 s, la voiture garde son DRS normal et reçoit en plus +12,5 % de batterie. Il faut d'abord trouver le champ de charge ERS dans l'objet voiture (même méthode qu'avec +0x86D).
3. **Case OVERTAKE** branchée sur l'étape 2.
4. **Aéro 2026** : gain du Straight Mode à 1,0 ou plus, appui en virage −30 % dans CarStats. À valider par des mesures de temps au tour.
5. **Zones FIA officielles** circuit par circuit.
