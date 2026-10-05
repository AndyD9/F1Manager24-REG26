"""Instantané de la grille, par position : écart avec la voiture devant, batterie, état ERS (+0x874 : 1 neutre,
2 recharge, 3 déploie), stratégie ERS (+0xEF2 : 0 Neutre, 1 Récupération, 2 Déploiement, 3 Top-Up), comportement
(+0x200), énergie déployée dans le tour (+0x888), crédit Overtake Mode et Overtake en cours.

  python grid.py [secondes] [intervalle]
"""
import struct, sys, time
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from monitor import read, find_cfg, STRIDE, GRID, find_pid, k32

STRAT = {0: "Neutre", 1: "Récup", 2: "Déploie", 3: "Top-Up"}


def snapshot(h, base, cfg):
    use = read(h, cfg, 32)
    credit = struct.unpack('<32f', read(h, cfg + 0x64, 128))
    rows = []
    for i in range(GRID):
        d = read(h, base + i * STRIDE, 0x1000)
        if d is None or d[0x710] != i:
            continue
        pos, lap = struct.unpack_from('<ii', d, 0x7E0)
        dist, speed = struct.unpack_from('<ff', d, 0x194)
        rows.append((pos, i, lap, dist, speed, struct.unpack_from('<f', d, 0x878)[0], d[0x874], d[0xEF2], d[0x200],
                     struct.unpack_from('<f', d, 0x888)[0]))
    rows.sort()
    prev = None
    for pos, i, lap, dist, speed, batt, ers, strat, mode, used in rows:
        gap = (prev - dist) / speed if prev is not None and speed > 1 else 0.0
        prev = dist
        print(f"P{pos + 1:<2d} voiture {i:2d} tour {lap:2d} écart {gap:5.2f} s  {speed * 3.6:3.0f} km/h  batterie {batt * 100:3.0f} %"
              f"  ERS {ers}  stratégie {STRAT.get(strat, strat):7s}  comportement {mode}  déployé {used:.2f}"
              f"  crédit {max(credit[i], 0) * 100:4.1f}{'  OVERTAKE' if use[i] else ''}")


def main():
    secs = float(sys.argv[1]) if len(sys.argv) > 1 else 0
    step = float(sys.argv[2]) if len(sys.argv) > 2 else 5
    pid = find_pid()
    h = k32.OpenProcess(0x0410, False, pid)
    cfg = find_cfg(h, pid)
    last = struct.unpack('<Q', read(h, cfg + 0x58, 8))[0]
    base = last - read(h, last + 0x710, 1)[0] * STRIDE
    t0 = time.time()
    while True:
        print(f"--- {time.time() - t0:.0f} s")
        snapshot(h, base, cfg)
        if time.time() - t0 + step > secs:
            break
        time.sleep(step)


if __name__ == '__main__':
    main()
