"""Suivi passif d'une course, toutes les 60 s : temps au tour (temps réel entre deux changements du compteur de tours,
jeu à vitesse 1 ; tours > 1,15 × la médiane ignorés), batterie de la grille, part du temps en déploiement, en
déploiement pour le chrono (g_cfg.push) et en Overtake Mode, stratégies ERS. Bilan à la fin.

  python session.py <secondes>
"""
import struct, sys, time
from collections import Counter
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from monitor import read, find_cfg, STRIDE, GRID, find_pid, k32
from laptimes import fmt

STRAT = {0: "Équilibré", 1: "L&C", 2: "Boost", 3: "Réserve"}


def summary(laps):
    if not laps:
        return "aucun tour"
    laps = sorted(laps)
    med = laps[len(laps) // 2]
    ok = [t for t in laps if t < med * 1.15]
    return f"{len(ok)} tours, meilleur {fmt(ok[0])}, médiane {fmt(ok[len(ok) // 2])}"


def main():
    secs = float(sys.argv[1]) if len(sys.argv) > 1 else 480
    pid = find_pid()
    h = k32.OpenProcess(0x0410, False, pid)
    cfg = find_cfg(h, pid)
    lastcar = struct.unpack('<Q', read(h, cfg + 0x58, 8))[0]
    base = lastcar - read(h, lastcar + 0x710, 1)[0] * STRIDE
    t0, nxt = time.time(), 60.0
    last, laps, all_laps = {}, [], []
    acc = Counter()
    batt_sum, batt_min = 0.0, 1.0
    strat = Counter()
    while time.time() - t0 < secs:
        now = time.time()
        use = read(h, cfg, 32)
        push = read(h, cfg + 0x10C, 32)
        for i in range(GRID):
            d = read(h, base + i * STRIDE, 0x1000)
            if d is None or d[0x710] != i:
                continue
            lap = struct.unpack_from('<i', d, 0x7E4)[0]
            if i in last and lap == last[i][0] + 1:
                if last[i][1] is not None:
                    laps.append(now - last[i][1])
                last[i] = (lap, now)
            elif i not in last or lap != last[i][0]:
                last[i] = (lap, None)
            if lap < 1 or struct.unpack_from('<f', d, 0x198)[0] < 1:
                continue
            b = struct.unpack_from('<f', d, 0x878)[0]
            acc["n"] += 1
            acc["deploie"] += d[0x874] == 3
            acc["push"] += push[i] != 0
            acc["overtake"] += use[i] != 0
            acc["bas"] += b < 0.25
            batt_sum += b
            batt_min = min(batt_min, b)
            strat[d[0xEF2]] += 1
        el = now - t0
        if el >= nxt and acc["n"]:
            n = acc["n"]
            st = ", ".join(f"{STRAT.get(s, s)} {c / n * 100:.0f} %" for s, c in sorted(strat.items()))
            print(f"[{el:4.0f} s] {summary(laps)} | batterie {batt_sum / n * 100:.0f} % (min {batt_min * 100:.0f}), "
                  f"sous 25 % {acc['bas'] / n * 100:.0f} % | déploie {acc['deploie'] / n * 100:.0f} %, chrono "
                  f"{acc['push'] / n * 100:.0f} %, overtake {acc['overtake'] / n * 100:.0f} % | {st}", flush=True)
            all_laps += laps
            laps, acc, strat = [], Counter(), Counter()
            batt_sum, batt_min = 0.0, 1.0
            nxt += 60.0
        time.sleep(0.1)
    all_laps += laps
    print(f"bilan : {summary(all_laps)}", flush=True)


if __name__ == '__main__':
    main()
