"""Répartition du temps par état de comportement (+0x200) et état ERS (+0x874 : 1 neutre, 2 recharge, 3 déploie),
avec vitesse et accélération moyennes, pour toute la grille.

  python ersstates.py <secondes>
"""
import struct, sys, time
from collections import defaultdict
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from monitor import read, find_cfg, STRIDE, GRID, find_pid, k32


def main():
    secs = float(sys.argv[1]) if len(sys.argv) > 1 else 60
    pid = find_pid()
    h = k32.OpenProcess(0x0410, False, pid)
    cfg = find_cfg(h, pid)
    last = struct.unpack('<Q', read(h, cfg + 0x58, 8))[0]
    base = last - read(h, last + 0x710, 1)[0] * STRIDE
    n = defaultdict(int)          # (comportement, ers) -> échantillons
    spd = defaultdict(float)
    acc = defaultdict(float)
    t0 = time.time()
    while time.time() - t0 < secs:
        for i in range(GRID):
            d = read(h, base + i * STRIDE, 0x900)
            if d is None or d[0x710] != i or struct.unpack_from('<i', d, 0x7E4)[0] < 1:
                continue
            k = (d[0x200], d[0x874])
            n[k] += 1
            v, a = struct.unpack_from('<ff', d, 0x198)
            spd[k] += v * 3.6
            acc[k] += a
        time.sleep(0.05)
    total = sum(n.values())
    print(f"{total} échantillons")
    for k in sorted(n):
        print(f"comportement {k[0]}  ERS {k[1]} : {n[k] / total * 100:5.1f} %  vitesse {spd[k] / n[k]:5.0f} km/h  "
              f"accélération {acc[k] / n[k]:+6.2f}")


if __name__ == '__main__':
    main()
