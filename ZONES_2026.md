# Zones Straight Mode 2026

Source : points de piste de chaque `Lvl_<circuit>.umap` (`scripts/analyze_straights.py` → `extract/tracks/straights.json`),
zones générées par `scripts/gen_zones_lua.py` dans `ue4ss/Reg2026/Scripts/zones.lua`.

**Règle** : on garde les zones DRS du jeu. Quand la FIA a annoncé le nombre de zones Straight Mode 2026 du circuit,
on ajoute les plus longues lignes droites restantes (400 m et plus, puis 200 m et plus) jusqu'à ce nombre.
Sinon, on ajoute toutes les lignes droites de 400 m et plus. Les zones ajoutées n'ont **pas** de point de détection
(en ajouter un provoque un drapeau rouge) : le jeu y enchaîne depuis la zone précédente.

Une **ligne droite** = une suite de points marqués `Straight` par le jeu.

## Nombre de zones par circuit

| Circuit | Zones du jeu | Ajoutées | Total | FIA 2026 |
|---|---|---|---|---|
| Australie | 4 | 0 | 4 | 5 |
| Bahreïn | 3 | 1 | 4 | — |
| Bakou | 2 | 0 | 2 | 2 |
| Barcelone | 2 | 2 | 4 | 4 |
| COTA | 2 | 1 | 3 | — |
| Canada | 3 | 0 | 3 | 3 |
| Mexique | 3 | 0 | 3 | — |
| Hungaroring | 2 | 2 | 4 | 4 |
| Imola | 1 | 2 | 3 | — |
| Interlagos | 2 | 1 | 3 | — |
| Djeddah | 3 | 1 | 4 | — |
| Singapour | 3 | 0 | 3 | — |
| Miami | 3 | 0 | 3 | 3 |
| Monaco | 1 | 0 | 1 | 0 |
| Monza | 2 | 2 | 4 | 4 |
| Qatar | 1 | 0 | 1 | — |
| Red Bull Ring | 3 | 1 | 4 | 4 |
| Shanghai | 2 | 2 | 4 | 4 |
| Silverstone | 2 | 2 | 4 | 4 |
| Spa | 2 | 3 | 5 | 5 |
| Suzuka | 1 | 1 | 2 | 2 |
| Las Vegas | 2 | 3 | 5 | — |
| Abou Dabi | 2 | 3 | 5 | — |
| Zandvoort | 2 | 0 | 2 | 2 |

Écarts : Australie 4 au lieu de 5 (pas d'autre ligne droite), Monaco 1 au lieu de 0 (la zone du jeu n'est pas retirée).

## Zones ajoutées (27)

| Circuit | Points | Longueur | Avant le virage |
|---|---|---|---|
| Bahreïn | 89 → 96 | 681 m | 14 |
| Barcelone | 17 → 19 | 328 m | 4 |
| Barcelone | 30 → 34 | 312 m | 7 |
| COTA | 28 → 31 | 454 m | 11 |
| Hungaroring | 41 → 45 | 327 m | 12 |
| Hungaroring | 90 → 3 | 545 m | 4 |
| Imola | 12 → 18 | 608 m | 6 |
| Imola | 52 → 56 | 421 m | 16 |
| Interlagos | 20 → 29 | 569 m | 6 |
| Djeddah | 22 → 29 | 657 m | 13 |
| Monza | 11 → 26 | 1 113 m | 4 |
| Monza | 66 → 78 | 1 126 m | 11 |
| Red Bull Ring | 43 → 49 | 584 m | 9 |
| Shanghai | 19 → 20 | 251 m | 5 |
| Shanghai | 44 → 45 | 259 m | 11 |
| Silverstone | 48 → 60 | 758 m | 9 |
| Silverstone | 67 → 73 | 478 m | 11 |
| Spa | 6 → 12 | 659 m | 2 |
| Spa | 41 → 43 | 385 m | 10 |
| Spa | 73 → 82 | 807 m | 17 |
| Suzuka | 69 → 78 | 800 m | 15 |
| Las Vegas | 1 → 4 | 654 m | 13 |
| Las Vegas | 17 → 21 | 635 m | 17 |
| Las Vegas | 64 → 68 | 435 m | 10 |
| Abou Dabi | 16 → 21 | 446 m | 5 |
| Abou Dabi | 50 → 56 | 479 m | 12 |
| Abou Dabi | 79 → 3 | 473 m | 1 |

Les numéros de virage viennent du jeu et peuvent différer légèrement de la numérotation officielle.
