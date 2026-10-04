# Zones Straight Mode 2026, proposition

Source : analyse des points de piste de chaque `Lvl_<circuit>.umap` (`scripts/analyze_straights.py`, résultats dans `extract/tracks/straights.json`).
Une **ligne droite** = une suite de points marqués `Straight` par le jeu, d'au moins **400 m**.

**Règle proposée** : Straight Mode = toutes les zones DRS actuelles + les nouvelles lignes droites ci-dessous.
Les points de détection actuels sont conservés et servent à l'**Overtake Mode** (moins d'1 s).

## Nouvelles zones (26)

| Circuit | Points | Longueur | Avant le virage |
|---|---|---|---|
| Bahreïn | 89 → 96 | 681 m | 14 |
| Bakou | 63 → 73 | 763 m | 15 |
| COTA | 28 → 31 | 454 m | 11 |
| Canada | 43 → 49 | 561 m | 10 |
| Canada | 18 → 25 | 427 m | 6 |
| Hungaroring | 90 → 3 | 545 m | 4 |
| Imola | 12 → 18 | 608 m | 6 |
| Imola | 52 → 56 | 421 m | 16 |
| Interlagos | 20 → 29 | 569 m | 6 |
| Djeddah | 22 → 29 | 657 m | 13 |
| Miami | 9 → 11 | 400 m | 4 |
| Monza | 66 → 78 | 1 126 m | 11 |
| Monza | 11 → 26 | 1 113 m | 4 |
| Red Bull Ring | 43 → 49 | 584 m | 9 |
| Silverstone | 48 → 60 | 758 m | 9 |
| Silverstone | 67 → 73 | 478 m | 11 |
| Spa | 73 → 82 | 807 m | 17 |
| Spa | 6 → 12 | 659 m | 2 |
| Suzuka | 69 → 78 | 800 m | 15 |
| Suzuka | 53 → 62 | 762 m | 13 |
| Las Vegas | 1 → 4 | 654 m | 13 |
| Las Vegas | 17 → 21 | 635 m | 17 |
| Las Vegas | 64 → 68 | 435 m | 10 |
| Abou Dabi | 50 → 56 | 479 m | 12 |
| Abou Dabi | 79 → 3 | 473 m | 1 |
| Abou Dabi | 16 → 21 | 446 m | 5 |

Les numéros de virage viennent du jeu et peuvent différer légèrement de la numérotation officielle.

## Circuits sans nouvelle zone

Albert Park, Barcelone, Mexico, Marina Bay, Monaco, Qatar, Shanghai, Zandvoort : leurs lignes droites de plus de 400 m sont déjà des zones DRS.

## Remarques

- **Djeddah** : les longues courbes à fond (zones DRS 61→70 et 82→93) ne sont pas marquées `Straight` par le jeu. Elles restent zones Straight Mode parce que ce sont déjà des zones DRS.
- **Spa 6 → 12** : c'est la descente après La Source, ce qui comprend **Eau Rouge**. On peut l'exclure par prudence.
