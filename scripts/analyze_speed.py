"""Compare les vitesses max en zone avec et sans forçage du Straight Mode (lignes MESURE; de UE4SS.log).

Usage : python scripts/analyze_speed.py [UE4SS.log]

Pour isoler l'effet du forçage, on ne garde que les passages SANS Overtake (le jeu n'aurait pas ouvert
le DRS de lui-même), et on compare zone par zone : moyenne « force » contre moyenne « normal ».
"""
import re
import sys
from collections import defaultdict
from pathlib import Path

LOG = Path(r"F:\SteamLibrary\steamapps\common\F1 Manager 2024\F1Manager24\Binaries\Win64\ue4ss\UE4SS.log")
LINE = re.compile(r"MESURE;([^;]+);(\d+);([^;]+);([^;]+);(\d+);([^;]+);([^;\s]+)(?:;([^;\s]+))?")


def main(path):
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    rows = [m.groups() for m in LINE.finditer(text)]
    if not rows:
        print("aucune mesure dans le journal")
        return
    print(f"{len(rows)} passages en zone mesurés, F7 utilisé {text.count('MESURE_F7;')} fois\n")

    # (circuit, zone, type) -> mode -> vitesses (passages sans overtake)
    # le jeu ouvre-t-il lui-même le DRS dans chaque zone (mode normal) ? -> il tient compte de la zone
    opened = defaultdict(lambda: [0, 0])
    for trk, zone, kind, _, _, mode, _, game in rows:
        if mode == "normal" and game is not None:
            opened[(trk, int(zone), kind)][1] += 1
            opened[(trk, int(zone), kind)][0] += game == "jeu"
    if opened:
        print("DRS ouvert par le jeu lui-même (mode normal) :")
        for (trk, zone, kind), (yes, total) in sorted(opened.items()):
            print(f"  {trk} zone {zone} ({kind}) : {yes}/{total} passages")
        print()

    groups = defaultdict(lambda: defaultdict(list))
    overtakes = 0
    for trk, zone, kind, driver, vmax, mode, ot, _ in rows:
        if ot == "overtake":
            overtakes += 1
            continue
        groups[(trk, int(zone), kind)][mode].append(int(vmax))

    print(f"{'circuit':<12} {'zone':>4} {'type':<8} {'forcé':>14} {'normal':>14} {'écart':>8}")
    deltas = []
    for (trk, zone, kind), modes in sorted(groups.items()):
        f, n = modes.get("force", []), modes.get("normal", [])

        def fmt(v):
            return f"{sum(v) / len(v):6.1f} ({len(v):>3})" if v else "      -       "

        delta = ""
        if f and n:
            d = sum(f) / len(f) - sum(n) / len(n)
            deltas.append(d)
            delta = f"{d:+6.1f}"
        print(f"{trk:<12} {zone:>4} {kind:<8} {fmt(f):>14} {fmt(n):>14} {delta:>8}")

    print(f"\n(passages avec Overtake exclus : {overtakes})")
    if deltas:
        avg = sum(deltas) / len(deltas)
        print(f"écart moyen forcé - normal : {avg:+.1f} km/h sur {len(deltas)} zones")
        print("=> le forçage change la vitesse" if abs(avg) >= 3 else
              "=> pas d'effet mesurable : le forçage ne change que l'affichage")
    else:
        print("il faut des passages dans les deux modes (F7) pour comparer")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else LOG)
