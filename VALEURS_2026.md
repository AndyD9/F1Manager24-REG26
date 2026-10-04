# Valeurs trouvées dans le jeu et proposition 2026

Moteur : **Unreal Engine 5.1** (pas 4.26). Version UAssetGUI : `VER_UE5_1`, retoc : `UE5_1`.
Mappings : `tools\Mappings.usmap` (copié aussi dans `%LocalAppData%\UAssetGUI\Mappings\F1M24.usmap`).

## 1. Straight Mode (aéro active)

### Zones : `Circuits/<Circuit>/Lvl_<Circuit>.umap` → objet `RaceSimTrackActor`

Exemple Bahreïn (3 zones) :

| Zone | Détection (nœud) | Début (nœud) | Fin (nœud) |
|---|---|---|---|
| 1 | 3 | 13 | 19 |
| 2 | 52 | 60 | 65 |
| 3 | 93 | 104 | 3 |

- Champs : `m_DRSDetection`, `m_DRSZoneStart`, `m_DRSZoneEnd`, chacun = `m_trackNodeID` + `m_splineDistance` (mètres après le nœud).
- La piste compte `m_trackNodesCount` nœuds, et `m_trackNodes` donne leurs positions. Ça permet de repérer les lignes droites.
- 24 circuits = 24 fichiers, ce qui correspond aux 24 packages de RRacing26SMZ.

**À faire** : ajouter une zone par grande ligne droite sur chaque circuit.

### Puissance de l'effet

| Fichier | Champ | Actuel | Proposé 2026 | Pourquoi |
|---|---|---|---|---|
| `RaceSim/DRSAccelerationSpeedCurce` | courbe : 0 km/h → 0 ; 360 km/h → **1,0** | 1,0 | **0,75** | Tout le monde l'a, donc gain plus petit pour ne pas casser les chronos |
| `RaceSimDataAsset` | `SlipstreamAccelerationMultiplier` | 1,08 | 1,10 | Aspiration plus forte : avec le Straight Mode pour tous, c'est elle qui crée l'écart de vitesse pour dépasser |
| `RaceSimDataAsset` | `DirtyAirMaxDist` | 220 | **150** | Voitures 2026 : moins d'air sale, on peut suivre de plus près |

### Écart de 1 seconde

**Introuvable dans les données.** Il est sûrement codé en dur dans le jeu. Piste de solution : un script UE4SS qui force `CarData.DRSState = 3` (ouvert) pour toutes les voitures dans les zones. Le « DRS mod » lit déjà ce champ, donc l'animation suivra.

## 2. ERS 2026 (350 kW, environ 50 % électrique)

| Fichier | Champ | Actuel | Proposé 2026 | Pourquoi |
|---|---|---|---|---|
| `RaceSimDataAsset` | `ERSAccelDeployBatteryRate` | −0,06 | **−0,10** | Règlement 2026 : 4 MJ à 350 kW durent 11,4 s, la batterie se vide en ~10 s de déploiement |
| `RaceSimDataAsset` | `ERSBrakingChargeBatteryRate` | 0,07 | **0,12** | Récupération environ doublée (8,5 MJ/tour) |
| `RaceSimDataAsset` | `ERSAccelerationMultiplier_Inactive` | 0,70 | **0,66** | Sans ERS, on perd un peu plus de puissance (0,55 et 0,62 écartaient trop le peloton) |
| `RaceSimDataAsset` | `ERSWearRate` | 13 | 15 | Plus sollicité |
| `DriverTacticsDataAsset` | `ERSDeployBudget` | 0,45 | 0,50 | Les pilotes utilisent plus l'électrique |
| `AI/RaceSimAIDataAsset` | `ERSChargingModeToggleThreshold` | 0,5 / 0,25 | 0,5 / 0,25 (inchangé) | 0,6 / 0,35 laissait l'IA en recharge trop longtemps, donc lente |

## 3. Overtake Mode

| Fichier | Champ | Actuel | Proposé 2026 |
|---|---|---|---|
| `RaceSimDataAsset` › OvertakeData | `OvertakeAssistOvertakeDifficultyModifier` | 0,125 | **0,25** |
| `RaceSimDataAsset` › OvertakeData | `SlipstreamTimeToOvertake` | 2,5 | 1,5 |
| `RaceSimDataAsset` › OvertakeData | `OvertakeMaxStartDistance` | 40 | 50 |
| `DriverTacticsDataAsset` | `OvertakeStrategyStatMultiplier` (agressif) | 1,2 | 1,3 |
| `OvertakeProbabilityAtSkillDifference` | courbe −40 → 0,10 ; +40 → 0,90 | | inchangée |

Un vrai Overtake Mode (+0,5 MJ si on est à moins d'1 s) demandera un script UE4SS (étape suivante).

## 4. Voitures 2026 (CarStatsDataAsset)

Poids actuels du calcul des stats voiture :
- Vitesse de pointe : `PowerWeight` 0,05 / `DragReductionWeight` 0,95
- Accélération : `PowerWeight` 0,5 / `DragReductionWeight` 0,5 / `MassWeight` 0,15

Proposition : accélération `PowerWeight` 0,6 (le moteur 2026 compte plus) et vitesse de pointe `PowerWeight` 0,15.
