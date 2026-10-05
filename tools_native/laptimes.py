"""Temps au tour de la grille (temps réel entre deux changements du compteur de tours +0x7E4, jeu à vitesse 1),
d'abord avec les réglages actuels, puis sans la limite de vitesse de déploiement (g_cfg.clipOn = 0, réécrit toutes
les 0,1 s ; remis à la fin). Ignore les tours anormaux (stands, voiture de sécurité : > 1,15 × la médiane).

  python laptimes.py <secondes_avant> <secondes_sans_limite>
"""
import struct, sys, time
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from monitor import read, find_cfg, STRIDE, GRID, find_pid, k32
from ersbudget import write


def fmt(t):
    return f"{int(t // 60)}:{t % 60:06.3f}"


def phase(h, base, cfg, secs, label, hold_off):
    clip = read(h, cfg + 0x20, 4)
    last = {}
    laps = []
    t0 = time.time()
    try:
        while time.time() - t0 < secs:
            if hold_off:
                write(h, cfg + 0x20, b'\0\0\0\0')
            now = time.time()
            for i in range(GRID):
                d = read(h, base + i * STRIDE, 0x800)
                if d is None or d[0x710] != i:
                    continue
                lap = struct.unpack_from('<i', d, 0x7E4)[0]
                if i in last and lap == last[i][0] + 1:
                    if last[i][1] is not None:
                        laps.append(now - last[i][1])
                    last[i] = (lap, now)
                elif i not in last or lap != last[i][0]:
                    last[i] = (lap, None)  # premier passage vu : départ du chrono au suivant
            time.sleep(0.05)
    finally:
        if hold_off:
            write(h, cfg + 0x20, clip)
    if not laps:
        print(f"{label} : aucun tour complet")
        return
    laps.sort()
    med = laps[len(laps) // 2]
    ok = [t for t in laps if t < med * 1.15]
    print(f"{label} : {len(ok)} tours, meilleur {fmt(ok[0])}, médiane {fmt(ok[len(ok) // 2])}, "
          f"moyenne {fmt(sum(ok) / len(ok))}", flush=True)


def main():
    before, without = float(sys.argv[1]), float(sys.argv[2])
    pid = find_pid()
    h = k32.OpenProcess(0x0438, False, pid)
    cfg = find_cfg(h, pid)
    lastcar = struct.unpack('<Q', read(h, cfg + 0x58, 8))[0]
    base = lastcar - read(h, lastcar + 0x710, 1)[0] * STRIDE
    phase(h, base, cfg, before, "réglages actuels", False)
    if without > 0:
        phase(h, base, cfg, without, "sans limite de 290 km/h", True)
        print("limite remise", flush=True)


if __name__ == '__main__':
    main()
