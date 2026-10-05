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
| **Overtake Mode** (< 1 s → +0,5 MJ) | `Reg2026Patch.dll` : à moins d'1 s, crédit de 12,5 % d'énergie en plus de la batterie, une fois par tour, pas avant 2 tours après le départ ou une relance (tour d'ouverture du DRS du jeu, +0x870 : sans ça, toute la grille l'avait au départ et les accrochages provoquaient des drapeaux rouges) ; gardé jusqu'à une vraie occasion (voiture devant à moins de 0,6 s, `overtake_ecart_attaque` ; avant le 2026-10-05, il partait dès 250 km/h après la détection, même loin derrière), puis déploiement ERS forcé à pleine puissance jusqu'à 337 km/h à chaque pas hors freinage, payé par le crédit (la cave de recharge exe+0x230856D, atteinte par tous les chemins, annule la baisse de batterie et décompte le crédit), au plus jusqu'à la fin du tour suivant | ✅ mesuré à Monza (2026-10-04) avec l'ancienne forme (+12,5 % ajoutés à la batterie, bornée à 100 %) : le déploiement forcé vide 7 à 9 % par pas, mais la grille arrive presque toujours à la ligne avec 94 à 100 % de batterie, donc le bonus était plafonné 3 fois sur 4 et n'agissait que quand l'IA passait par sa décision ERS (35 à 100 % des pas). Le crédit (2026-10-04 soir) corrige les deux points, ✅ mesuré à Monza le soir même par pas de simulation : la batterie reste à 100 % pendant le bonus (ou remonte au freinage), l'état ERS passe à 3 avec débit −0,10 (pleine puissance), le crédit baisse de 0,33 point par appel de la mise à jour ERS (0,10 × 1/30) et les 12,5 % sont consommés en ~37 appels, soit 1,2 à 1,5 s de simulation (0,5 MJ à 350 kW durent 1,4 s), donc 1 à 2 pas. 70 attributions en 5 tours, aucune erreur Lua |
| **Overtake Mode** : avantage au dépassement | `Reg2026Patch.dll` : dans l'évaluation d'un dépassement (exe+0x231F8B0), le jeu ajoute 0,2 à la probabilité de réussite quand l'attaquant a le DRS et pas le défenseur (OvertakeData +0x3C, champ absent du JSON ; `OvertakeAssistOvertakeDifficultyModifier` est autre chose). Avec le Straight Mode pour tous, les deux ont le DRS et ce bonus ne s'appliquait plus jamais. La cave en 231FBFE le donne à l'attaquant qui a franchi une détection à moins d'1 s (voiture r14, confirmée derrière la r15 au point d'arrêt), quel que soit le DRS du défenseur ; F7 rend le test d'origine. L'avantage dure 2 km après chaque détection à moins d'1 s (`overtake_distance`), indépendamment du crédit d'énergie (un par tour) : mesuré à Monza, le crédit (1,4 s) est dépensé avant que le jeu n'évalue le dépassement (64 évaluations en 2 min, aucune pendant un déploiement). Jusqu'au 2026-10-05, il s'arrêtait à la fin du tour : sur 20 circuits sur 24, une zone passe la ligne (Monza : détection avant la Parabolica, fin de zone au virage 1), le bonus était perdu avant l'évaluation, et la 2e détection d'un tour ne donnait rien. Entre une détection et la fin de sa zone : 0,6 à 1,8 km (Imola) | ✅ mesuré à Monza le 2026-10-05 au matin : `state.json` montre l'avantage maintenu après l'épuisement du crédit jusqu'à la fin du tour ; au point d'arrêt sur le test (231FC2B), l'évaluation capturée a bien cl = 1 (bonus appliqué) ; sur 2 × 130 s aux tours 1-4, 12 places gagnées sur 16 l'ont été par une voiture ayant eu l'Overtake Mode dans la minute. Les évaluations sont rares quand la grille est étirée (1 à 5 en 2 min, contre 64 après une relance de voiture de sécurité) |
| Case OVERTAKE du bandeau | Interface : écart avec la voiture devant lu dans le classement au passage de la ligne ; à moins d'1 s, allumée pendant le tour (la recharge au freinage fait des sauts de batterie aussi grands que le bonus, on ne peut pas s'y fier) | 🧪 à voir en course |
| 350 kW, 50 % électrique | Pak et script : `ERSAccelDeployBatteryRate` −0,10, `ERSAccelerationMultiplier_Inactive` 0,75 | ✅ batterie vide en ~10 s de déploiement (4 MJ à 350 kW = 11,4 s) ; temps au tour à Monza mesuré en direct (2026-10-05) : 0,66 -> 1:29.0 de médiane, 0,80 -> 1:24.9, 1,0 -> 1:20.0 (vrai GP 2026 : 1:23.504 au meilleur tour) : l'IA ne déploie que ~10 % du temps. Gardé à 0,66 : le rythme vient du déploiement pour le chrono (BOOST / ÉQUILIBRÉ, Reg2026Patch.dll), 🧪 à vérifier (0,55 et 0,62 écartaient trop le peloton) |
| 8,5 MJ récupérés par tour, 350 kW au freinage | Pak et script : `ERSBrakingChargeBatteryRate` 0,0875 (350 kW) ; recharge du super clipping 0,00035 | 🧪 mesuré en direct à Monza (2026-10-05) : avec 0,12 et 0,0007 la batterie restait pleine (89 % de moyenne, jamais sous 62 %), l'énergie ne comptait pas ; avec 0,0875 et 0,00035, ~80 % de moyenne, des voitures sous 40 %. L'IA ne déploie qu'en sortie de virage (~1 batterie par tour, son plan de déploiement n'est pas la limite) |
| Puissance électrique réduite au-delà de 290 km/h, super clipping (recharge à fond en bout de ligne droite) | Limite toujours active avec la règle 2026 (depuis le 2026-10-05 : sans elle, l'Overtake Mode n'avait aucun avantage de vitesse de pointe) : plus de déploiement au-delà de 290 km/h (337 en Overtake Mode, payé par le crédit). Recharge optionnelle (`superclipping.ini` actif=1, F6) : au-dessus, à fond, recharge 0,0007 par appel ERS (~+2 % par pas de simulation pour un déploiement à −3 %, rapport 250 kW / 350 kW) | ✅ mesuré à Monza : 0 déploiement au-delà de 290 km/h, recharge +1,8 % par pas à 0,0006 |
| Appui −30 % (−30 kg) | Pak : `AeroSpeedMultipliers` virages lents −2 %, moyens −5 %, rapides −8 % | 🧪 à valider par des temps au tour |
| Moins d'air sale (90 % d'appui à 20 m) | Pak : `DirtyAirMaxDist` 150 (220), `DirtyAirSpeedMultipliers` 0,93 (0,90) | ✅ |
| Boost manuel | Stratégie ERS **BOOST** (ex-Déploiement, comportement du jeu, stratégie de course de l'IA) | ✅ |
| Gestion de l'énergie | Stratégies ERS renommées (`ui_mod`, Reg2026Texts.js) et comportements dans `Reg2026Patch.dll` (stratégie en +0xEF2) : **ÉQUILIBRÉ** (ex-Neutre, jeu) ; **RÉSERVE** (ex-Top-Up) : pas de déploiement sauf Overtake Mode ou défense, voiture à moins d'1 s derrière (positions +0x7E0, distance +0x194) ; **LIFT & COAST** (ex-Récupération) : plus d'électrique au-delà de 250 km/h et recharge au-dessus | ✅ mesuré à Monza (2026-10-04) : RÉSERVE 18 déploiements sur 373 pas, tous à moins d'1 s d'une autre voiture ; LIFT & COAST 0 déploiement sur 155 pas au-delà de 250 km/h |

## 4. Reste à faire

- Valider l'aéro par des temps au tour (pak actuel contre `build/backup_pak_v1`) et ajuster.
- Dépassements : avec le Straight Mode pour tous, l'écart de vitesse vient de l'aspiration (1,10), de la difficulté de dépassement (0,25) et du déploiement forcé d'Overtake Mode. À valider en course.
- Monaco sans zone : retirer la zone du jeu demande de toucher aux points de détection (risque de drapeau rouge).
