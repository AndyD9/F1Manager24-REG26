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
| Straight Mode pour tous, sans écart | `Reg2026Patch.dll` : le test « > 1 s » au point de détection est contourné | ✅ mesuré à Monza (toute la grille au niveau « avec DRS ») |
| Dès le 1er tour | `Reg2026Patch.dll` : condition de tour neutralisée (exe+0x230C335, objet voiture +0x870) | ✅ vu en course (DRS et bonus dès le tour 1) |
| Zones Straight Mode désignées | Zones du jeu + zones ajoutées, au nombre annoncé par la FIA quand il est connu (ZONES_2026.md) | ✅ sauf Australie (4/5 : pas d'autre ligne droite) et Monaco (zone du jeu gardée) |
| Sous voiture de sécurité (si sec) | Le jeu bloque | ➖ blocage gardé : aucun effet utile à vitesse de safety car |
| Pluie : mode partiel | Le jeu bloque sur piste mouillée | ➖ approximation |
| Gain du Straight Mode (avant + arrière, traînée −55 %) | Pak : courbe DRS d'origine, `DRSTopSpeedMultiplier` 1,03–1,06 (1,016–1,043), `DRSAccelerationMultiplier` 1,05–1,20 (1,0–1,146) | 🧪 à valider par des temps au tour |
| **Overtake Mode** (< 1 s → +0,5 MJ) | `Reg2026Patch.dll` : à moins d'1 s, +12,5 % de batterie (objet voiture +0x878), une fois par tour | ✅ vu en course (patch.log) |
| Case OVERTAKE du bandeau | Interface : écart avec la voiture devant lu dans le classement au passage de la ligne ; à moins d'1 s, allumée pendant le tour (la recharge au freinage fait des sauts de batterie aussi grands que le bonus, on ne peut pas s'y fier) | 🧪 à voir en course |
| 350 kW, 50 % électrique | Pak : `ERSAccelDeployBatteryRate` −0,10, `ERSAccelerationMultiplier_Inactive` 0,55 | ✅ cohérent : batterie vide en ~10 s, 4 MJ à 350 kW durent 11,4 s |
| 8,5 MJ récupérés par tour | Pak : `ERSBrakingChargeBatteryRate` 0,12 | ✅ ordre de grandeur correct (~2 batteries par tour) |
| Puissance électrique réduite au-delà de 290 km/h | Pas d'équivalent dans le jeu (multiplicateur d'accélération) | ➖ non reproduit |
| Appui −30 % (−30 kg) | Pak : `AeroSpeedMultipliers` virages lents −2 %, moyens −5 %, rapides −8 % | 🧪 à valider par des temps au tour |
| Moins d'air sale (90 % d'appui à 20 m) | Pak : `DirtyAirMaxDist` 150 (220), `DirtyAirSpeedMultipliers` 0,93 (0,90) | ✅ |
| Boost manuel | Modes ERS du jeu | ✅ existe déjà |

## 4. Reste à faire

- Valider l'aéro par des temps au tour (pak actuel contre `build/backup_pak_v1`) et ajuster.
- Monaco sans zone : retirer la zone du jeu demande de toucher aux points de détection (risque de drapeau rouge).
