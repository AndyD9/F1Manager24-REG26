"""Repère les lignes droites de chaque circuit à partir des points de piste (RaceSimTrackComponent).

Usage : python scripts/analyze_straights.py [json ...]   (par défaut : extract/tracks/json/*.json)
Écrit extract/tracks/straights.json et affiche un résumé.
"""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MIN_LENGTH_M = 400  # longueur minimale d'une ligne droite retenue


def find_prop(node, name):
    """Premier dict {Name: name} trouvé (parcours en profondeur)."""
    if isinstance(node, dict):
        if node.get("Name") == name and "Value" in node:
            return node
        for v in node.values():
            r = find_prop(v, name)
            if r is not None:
                return r
    elif isinstance(node, list):
        for v in node:
            r = find_prop(v, name)
            if r is not None:
                return r
    return None


def fields(struct_prop):
    out = {}
    for p in struct_prop["Value"]:
        v = p["Value"]
        if isinstance(v, list) and v and isinstance(v[0], dict) and "X" in (v[0].get("Value") or {}):
            v = v[0]["Value"]
        out[p["Name"]] = v
    return out


def positions(track_comp, name):
    prop = find_prop(track_comp, name)
    return [(int(f["m_trackNodeID"]), float(str(f["m_splineDistance"]).replace("+", "")))
            for f in (fields(e) for e in prop["Value"])] if prop else []


def scalar(track_comp, name):
    p = find_prop(track_comp, name)
    return None if p is None else p["Value"]


STRAIGHT = 3  # EBendType::Straight


def analyze(path):
    """path : .uexp du niveau (lecture binaire directe)."""
    from track_binary import find_component
    comp = find_component(Path(path).read_bytes())
    count = comp["m_trackNodesCount"]
    nodes = comp["m_trackNodes"][:count]  # les points suivants sont la voie des stands
    pos = [nd["m_pos"] for nd in nodes]
    n = len(nodes)
    # distance (m) du point i au point i+1 (les ID suivent l'ordre du tour)
    seg = [math.dist(pos[i], pos[(i + 1) % n]) / 100 for i in range(n)]
    straight = [nd["m_cornerType"] == STRAIGHT for nd in nodes]

    # séquences de points "Straight" consécutifs (en boucle)
    runs = []
    if not all(straight):
        start = next(i for i in range(n) if not straight[i])  # commencer après un virage
        i, cur = (start + 1) % n, None
        for _ in range(n):
            if straight[i] and cur is None:
                cur = [i]
            elif straight[i]:
                cur.append(i)
            elif cur is not None:
                runs.append(cur); cur = None
            i = (i + 1) % n
        if cur is not None:
            runs.append(cur)
    result = []
    for r in runs:
        # longueur : du premier point droit jusqu'au point suivant le dernier (entrée du virage)
        length = sum(seg[j] for j in r)
        end_node = (r[-1] + 1) % n
        result.append(dict(first=r[0], last=r[-1], brake_node=end_node, length_m=round(length),
                           corner_after=int(nodes[end_node]["m_cornerNumber"]),
                           max_speed=max(float(nodes[j]["m_maxSpeed"]) for j in r)))
    result.sort(key=lambda s: -s["length_m"])
    def tp(name):
        return [(p["m_trackNodeID"], p["m_splineDistance"]) for p in comp[name]]

    return dict(
        nodes=n,
        lap_m=round(sum(seg)),
        max_jump_m=round(max(seg)),
        drs_detection=tp("m_DRSDetection"),
        drs_start=tp("m_DRSZoneStart"),
        drs_end=tp("m_DRSZoneEnd"),
        node_dist_m=[round(sum(seg[:i]), 1) for i in range(n)],  # distance depuis le point 0
        straights=[s for s in result if s["length_m"] >= MIN_LENGTH_M],
    )


def in_run(node, s, n, margin=3):
    """Le point est dans la ligne droite (ou jusqu'à `margin` points avant son début)."""
    a, b = (s["first"] - margin) % n, s["last"]
    return a <= node <= b if a <= b else (node >= a or node <= b)


def main(paths):
    report = {}
    for p in paths:
        name = Path(p).stem.replace("Lvl_", "")
        try:
            t = analyze(p)
        except Exception as e:  # noqa: BLE001
            print(f"{name}: erreur {e}")
            continue
        report[name] = t
        print(f"\n== {name} : {t['nodes']} points, tour {t['lap_m']} m (plus grand écart entre points {t['max_jump_m']} m)")
        print(f"   zones DRS actuelles : " + ", ".join(
            f"{s[0]}->{e[0]}" for s, e in zip(t["drs_start"], t["drs_end"])) or "aucune")
        for s in t["straights"]:
            drs = any(in_run(z[0], s, t["nodes"]) for z in t["drs_start"])
            print(f"   ligne droite {s['length_m']:>5} m  points {s['first']:>3}->{s['last']:<3} "
                  f"avant virage {s['corner_after']:<2}  {'(déjà DRS)' if drs else ''}")
    out = ROOT / "extract" / "tracks" / "straights.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1), encoding="utf-8")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    args = sys.argv[1:] or sorted(str(p) for p in (ROOT / "extract" / "tracks" / "legacy").rglob("Lvl_*.uexp"))
    main(args)
