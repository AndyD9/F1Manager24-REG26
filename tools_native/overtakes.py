"""Compte les changements de position et dit si la voiture qui gagne une place était en Overtake Mode
dans les N dernières secondes (4 par défaut).

  python overtakes.py <objet_voiture_hex> <secondes> [fenêtre_s]
"""
import struct, sys, time
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from monitor import read, find_cfg, STRIDE, GRID, find_pid, k32


def main():
    car0 = int(sys.argv[1], 16)
    secs = float(sys.argv[2]) if len(sys.argv) > 2 else 120
    window = float(sys.argv[3]) if len(sys.argv) > 3 else 4.0
    pid = find_pid()
    h = k32.OpenProcess(0x0410, False, pid)
    base = car0 - read(h, car0 + 0x710, 1)[0] * STRIDE
    cfg = find_cfg(h, pid)
    t0 = time.time()
    prevpos = {}
    lastboost = {}
    gains = {"overtake": 0, "sans": 0}
    while time.time() - t0 < secs:
        now = time.time() - t0
        boost = read(h, cfg, 0x20)
        pos = {}
        for i in range(GRID):
            d = read(h, base + i * STRIDE, 0x900)
            if d is None or d[0x710] != i:
                continue
            p = struct.unpack_from('<i', d, 0x7E0)[0]
            if 0 <= p < GRID:
                pos[i] = (p, struct.unpack_from('<i', d, 0x7E4)[0], d[0x200])
            if boost[i]:
                lastboost[i] = now
        for i, (p, lap, mode) in pos.items():
            if i in prevpos and p < prevpos[i][0]:
                recent = now - lastboost.get(i, -99) < window
                gains["overtake" if recent else "sans"] += 1
                print(f"[{now:6.1f}s] voiture {i:2d} gagne P{prevpos[i][0]+1} -> P{p+1} au tour {lap} "
                      f"{'(Overtake Mode il y a %.1f s)' % (now - lastboost[i]) if recent else '(sans Overtake Mode)'}")
            prevpos[i] = (p, lap, mode)
        time.sleep(0.1)
    print("places gagnées :", gains)


if __name__ == '__main__':
    main()
