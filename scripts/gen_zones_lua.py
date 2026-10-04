"""Génère ue4ss/Reg2026/Scripts/zones.lua à partir de extract/tracks/straights.json.

Pour chaque circuit :
  nodes     = nombre de points de piste
  existing  = zones DRS d'origine (déjà dans le jeu)
  added     = nouvelles zones Straight Mode (lignes droites >= 400 m pas encore DRS)
Chaque zone : { s = point de début, sd = distance (m), e = point de fin, ed = distance (m) }
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "extract" / "tracks" / "straights.json"
OUT = ROOT / "ue4ss" / "Reg2026" / "Scripts" / "zones.lua"
END_RATIO = 0.7  # la zone s'arrête à 70 % du dernier segment, avant le freinage

# Nombre de zones Straight Mode annoncé par la FIA pour 2026 (REGLEMENT_2026.md). Les zones DRS du jeu sont
# gardées ; on ajoute les plus longues lignes droites restantes jusqu'au nombre visé, ou on retire les zones
# ajoutées en trop. Circuits absents : toutes les lignes droites de 400 m et plus.
FIA_ZONES = {
    "AlbertPark": 5, "Shanghai": 4, "Suzuka": 2, "Miami": 3, "GillesVilleneuve": 3, "Monaco": 0,
    "Barcelona": 4, "RedBullRing": 4, "Silverstone": 4, "SpaFrancorchamps": 5, "Hungaroring": 4,
    "Zandvoort": 2, "Monza": 4, "Baku": 2,
}


def in_run(node, s, n, margin=8):
    a, b = (s["first"] - margin) % n, s["last"]
    return a <= node <= b if a <= b else (node >= a or node <= b)


def main():
    tracks = json.loads(SRC.read_text(encoding="utf-8"))
    lines = ["-- Généré par scripts/gen_zones_lua.py, ne pas modifier à la main.", "return {"]
    total_added = 0
    for name, t in sorted(tracks.items()):
        n, dist, lap = t["nodes"], t["node_dist_m"], t["lap_m"]

        def seg(i):
            nxt = dist[(i + 1) % n] if i + 1 < n else lap
            return nxt - dist[i]

        existing = [dict(s=s[0], sd=round(s[1], 1), e=e[0], ed=round(e[1], 1))
                    for s, e in zip(t["drs_start"], t["drs_end"])]
        def free(runs):
            return [st for st in runs if not any(in_run(z[0], st, n) for z in t["drs_start"])]

        # candidates de la plus longue à la plus courte
        candidates = free(t["straights"])
        target = FIA_ZONES.get(name)
        if target is None:
            chosen = candidates
        else:
            candidates += free(t.get("short_straights", []))
            chosen = candidates[:max(0, target - len(existing))]
            if target < len(existing):
                print(f"{name} : la FIA prévoit {target} zone(s), le jeu en a {len(existing)} (gardées)")
        added = [dict(s=st["first"], sd=0.0, e=st["last"], ed=round(seg(st["last"]) * END_RATIO, 1))
                 for st in sorted(chosen, key=lambda st: st["first"])]
        if target is not None and len(existing) + len(added) != target:
            print(f"{name} : {len(existing) + len(added)} zones au lieu de {target} (pas assez de lignes droites)")
        total_added += len(added)

        def fmt(zs):
            return ", ".join(f"{{s={z['s']}, sd={z['sd']}, e={z['e']}, ed={z['ed']}}}" for z in zs)

        lines.append(f"  {name} = {{ nodes = {n}, existing = {{ {fmt(existing)} }}, added = {{ {fmt(added)} }} }},")
    lines.append("}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{OUT} : {len(tracks)} circuits, {total_added} zones ajoutées")


if __name__ == "__main__":
    main()
