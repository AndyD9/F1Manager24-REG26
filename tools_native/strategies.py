"""Changements de stratégie ERS de l'IA (+0xEF2 : 0 Neutre, 1 Récupération, 2 Déploiement, 3 Top-Up = RÉSERVE du
mod), avec la batterie au moment du changement, et part du temps passé dans chaque stratégie.

  python strategies.py <secondes>
"""
import struct, sys, time
from collections import Counter
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from monitor import read, find_cfg, STRIDE, GRID, find_pid, k32

STRAT = {0: "Neutre", 1: "Récupération", 2: "Déploiement", 3: "Top-Up"}


def main():
    secs = float(sys.argv[1]) if len(sys.argv) > 1 else 90
    pid = find_pid()
    h = k32.OpenProcess(0x0410, False, pid)
    cfg = find_cfg(h, pid)
    last = struct.unpack('<Q', read(h, cfg + 0x58, 8))[0]
    base = last - read(h, last + 0x710, 1)[0] * STRIDE
    prev, time_in, t0 = {}, Counter(), time.time()
    while time.time() - t0 < secs:
        for i in range(GRID):
            d = read(h, base + i * STRIDE, 0x1000)
            if d is None or d[0x710] != i or struct.unpack_from('<f', d, 0x198)[0] < 1:
                continue
            s, b = d[0xEF2], struct.unpack_from('<f', d, 0x878)[0]
            time_in[s] += 1
            if i in prev and prev[i] != s:
                print(f"[{time.time() - t0:5.1f} s] voiture {i:2d} : {STRAT.get(prev[i])} -> {STRAT.get(s)} "
                      f"(batterie {b * 100:.0f} %)", flush=True)
            prev[i] = s
        time.sleep(0.2)
    total = sum(time_in.values())
    print("temps par stratégie : " + ", ".join(f"{STRAT.get(s)} {n / total * 100:.0f} %" for s, n in sorted(time_in.items())))


if __name__ == '__main__':
    main()
