"""Applique les valeurs du règlement 2026 (voir VALEURS_2026.md) aux JSON UAssetGUI.

Lit extract/json/<Asset>.json, écrit build/json/<Asset>.json.
Chaque modification vérifie la valeur d'origine pour ne pas patcher le mauvais champ.
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "extract" / "json"
DST = ROOT / "build" / "json"

# Asset -> liste de (nom du champ, numéro d'occurrence, valeur d'origine, nouvelle valeur)
PATCHES = {
    "RaceSimDataAsset": [
        ("ERSAccelDeployBatteryRate", 0, -0.06, -0.10),
        ("ERSBrakingChargeBatteryRate", 0, 0.07, 0.12),
        ("ERSAccelerationMultiplier_Inactive", 0, 0.70, 0.66),
        ("ERSWearRate", 0, 13.0, 15.0),
        ("SlipstreamAccelerationMultiplier", 0, 1.08, 1.10),
        ("DirtyAirMaxDist", 0, 220.0, 150.0),
        ("OvertakeAssistOvertakeDifficultyModifier", 0, 0.125, 0.25),
        ("SlipstreamTimeToOvertake", 0, 2.5, 1.5),
        ("OvertakeMaxStartDistance", 0, 40.0, 50.0),
    ],
    "DriverTacticsDataAsset": [
        ("ERSDeployBudget", 0, 0.45, 0.50),
        ("OvertakeStrategyStatMultiplier", 0, 1.2, 1.3),
    ],
    "RaceSimAIDataAsset": [
        ("ERSChargingModeToggleThreshold", 0, 0.5, 0.5),
        ("ERSChargingModeToggleThreshold", 1, 0.25, 0.25),
    ],
    "CarStatsDataAsset": [
        # Vitesse de pointe (somme = 1)
        ("PowerWeight", 0, 0.05, 0.15),
        ("DragReductionWeight", 0, 0.95, 0.85),
        # Accélération (Power + Drag = 1, Mass à part)
        ("PowerWeight", 1, 0.5, 0.6),
        ("DragReductionWeight", 1, 0.5, 0.4),
    ],
}

# Vecteurs (X = voiture la moins bonne, Y = la meilleure) : asset -> (champ, occurrence, (X, Y) d'origine, nouveau)
# Aéro 2026 (REGLEMENT_2026.md) : appui −30 % compensé en partie par −30 kg, donc vitesse en virage un peu
# plus basse, surtout en courbe rapide ; moins d'air sale ; Straight Mode (avant + arrière, traînée −55 %)
# nettement plus efficace que l'ancien DRS.
VEC_PATCHES = {
    "CarStatsDataAsset": [
        ("AeroSpeedMultipliers", 0, (0.831, 0.964), (0.814, 0.945)),  # virages lents −2 %
        ("AeroSpeedMultipliers", 1, (0.769, 1.0), (0.731, 0.95)),      # virages moyens −5 %
        ("AeroSpeedMultipliers", 2, (0.834, 1.0), (0.767, 0.92)),      # virages rapides −8 %
        ("DirtyAirSpeedMultipliers", 0, (0.9, 1.0), (0.93, 1.0)),
        ("DirtyAirSpeedMultipliers", 1, (0.9, 1.0), (0.93, 1.0)),
        ("DirtyAirSpeedMultipliers", 2, (0.9, 1.0), (0.93, 1.0)),
        ("DRSTopSpeedMultiplier", 0, (1.0155, 1.0431), (1.03, 1.06)),
        ("DRSAccelerationMultiplier", 0, (1.0, 1.146), (1.05, 1.20)),
    ],
}

# Courbe DRS : None = courbe d'origine du jeu (gain du Straight Mode réglé par VEC_PATCHES)
DRS_CURVE = None


def find_props(node, name, found):
    if isinstance(node, dict):
        if node.get("Name") == name and "Value" in node and not isinstance(node["Value"], (dict, list)):
            found.append(node)
        for v in node.values():
            find_props(v, name, found)
    elif isinstance(node, list):
        for v in node:
            find_props(v, name, found)
    return found


def find_curve_keys(node, found):
    if isinstance(node, dict):
        if "Time" in node and "ArriveTangent" in node:
            found.append(node)
        for v in node.values():
            find_curve_keys(v, found)
    elif isinstance(node, list):
        for v in node:
            find_curve_keys(v, found)
    return found


def find_vectors(node, name, found):
    if isinstance(node, dict):
        if node.get("Name") == name and isinstance(node.get("Value"), dict) and "X" in node["Value"]:
            found.append(node)
        for v in node.values():
            find_vectors(v, name, found)
    elif isinstance(node, list):
        for v in node:
            find_vectors(v, name, found)
    return found


def as_float(v):
    return float(str(v).replace("+", ""))


def close(a, b):
    return math.isclose(a, b, rel_tol=1e-4, abs_tol=1e-6)


def main():
    DST.mkdir(parents=True, exist_ok=True)
    for asset in sorted(set(PATCHES) | set(VEC_PATCHES)):
        data = json.loads((SRC / f"{asset}.json").read_text(encoding="utf-8"))
        for name, occ, old, new in VEC_PATCHES.get(asset, []):
            vec = find_vectors(data["Exports"], name, [])[occ]["Value"]
            cur = (as_float(vec["X"]), as_float(vec["Y"]))
            assert close(cur[0], old[0]) and close(cur[1], old[1]), f"{asset}.{name}[{occ}] = {cur}, attendu {old}"
            vec["X"], vec["Y"] = new
            print(f"{asset}.{name}[{occ}]: {cur} -> {new}")
        patches = PATCHES.get(asset, [])
        for name, occ, old, new in patches:
            props = find_props(data["Exports"], name, [])
            prop = props[occ]
            cur = as_float(prop["Value"])
            assert close(cur, old), f"{asset}.{name}[{occ}] = {cur}, attendu {old}"
            prop["Value"] = new
            print(f"{asset}.{name}[{occ}]: {cur:g} -> {new:g}")
        (DST / f"{asset}.json").write_text(json.dumps(data, indent=2), encoding="utf-8")

    if DRS_CURVE is None:
        # courbe d'origine : le fichier reste celui du jeu
        asset = "DRSAccelerationSpeedCurce"
        (DST / f"{asset}.json").write_text((SRC / f"{asset}.json").read_text(encoding="utf-8"), encoding="utf-8")
        print(f"{asset}: courbe d'origine")
        return
    asset, t, old, new = DRS_CURVE
    data = json.loads((SRC / f"{asset}.json").read_text(encoding="utf-8"))
    keys = [k for k in find_curve_keys(data["Exports"], []) if close(as_float(k["Time"]), t)]
    assert len(keys) == 1 and close(as_float(keys[0]["Value"]), old), "clé DRS introuvable"
    k = keys[0]
    ratio = new / old
    k["Value"] = new
    for tan in ("ArriveTangent", "LeaveTangent"):
        if tan in k:
            k[tan] = as_float(k[tan]) * ratio
    # la tangente de la clé à 0 km/h suit aussi la nouvelle pente
    for k0 in find_curve_keys(data["Exports"], []):
        if close(as_float(k0["Time"]), 0.0):
            for tan in ("ArriveTangent", "LeaveTangent"):
                if tan in k0:
                    k0[tan] = as_float(k0[tan]) * ratio
    print(f"{asset}: clé {t:g} km/h {old:g} -> {new:g}")
    (DST / f"{asset}.json").write_text(json.dumps(data, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
