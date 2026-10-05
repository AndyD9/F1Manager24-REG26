"""Avantage au dépassement (g_cfg.assist de Reg2026Patch.dll) aux endroits du tour où le jeu évalue les dépassements.

À chaque passage d'une voiture à une distance donnée depuis la ligne (mètres, en fin de zone : Monza 570 = freinage du
virage 1, 3560 = freinage d'Ascari), affiche l'avantage (a), le crédit restant et l'écart avec la voiture devant.
La distance depuis la ligne est mesurée à partir du changement du compteur de tours (+0x7E4) : une voiture n'est
comptée qu'après son premier passage de la ligne pendant la mesure. L'objet voiture est lu dans g_cfg.lastCar.

  python assist.py <secondes> <distance_m> [<distance_m> ...]
"""
import struct, sys, time
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from monitor import read, find_cfg, STRIDE, GRID, find_pid, k32


def main():
    secs = float(sys.argv[1])
    marks = [float(x) for x in sys.argv[2:]] or [570.0]
    pid = find_pid()
    h = k32.OpenProcess(0x0410, False, pid)
    cfg = find_cfg(h, pid)
    if not cfg:
        sys.exit("g_cfg introuvable")
    last = struct.unpack('<Q', read(h, cfg + 0x58, 8))[0]
    base = last - read(h, last + 0x710, 1)[0] * STRIDE
    print(f"g_cfg {cfg:X}, voitures {base:X}")
    t0 = time.time()
    line = {}   # idx -> (tour, distance au passage de la ligne)
    prev = {}   # idx -> distance depuis la ligne à l'échantillon précédent
    stats = {m: {"proche_a": 0, "proche_sans": 0, "loin_a": 0, "loin_sans": 0} for m in marks}
    while time.time() - t0 < secs:
        assist = read(h, cfg + 0xEC, 32)
        credit = struct.unpack('<32f', read(h, cfg + 0x64, 128))
        cars = {}
        for i in range(GRID):
            d = read(h, base + i * STRIDE, 0x800)
            if d is None or d[0x710] != i:
                continue
            dist, speed = struct.unpack_from('<ff', d, 0x194)
            pos, lap = struct.unpack_from('<ii', d, 0x7E0)
            cars[i] = (dist, speed, pos, lap)
        by_pos = {c[2]: (i, c) for i, c in cars.items()}
        for i, (dist, speed, pos, lap) in cars.items():
            if i not in line or line[i][0] != lap:
                if i in line:
                    line[i] = (lap, dist)
                    prev[i] = 0.0
                else:
                    line[i] = (lap, None)  # tour en cours : distance de la ligne inconnue
                continue
            if line[i][1] is None:
                continue
            s = dist - line[i][1]
            for m in marks:
                if prev.get(i, s) < m <= s:
                    ahead = by_pos.get(pos - 1)
                    gap = (ahead[1][0] - dist) / speed if ahead and speed > 1 else None
                    near = gap is not None and 0 < gap < 1.0
                    a = assist[i]
                    stats[m][("proche" if near else "loin") + ("_a" if a else "_sans")] += 1
                    g = f"{gap:5.2f} s" if gap is not None else "  tête"
                    print(f"[{time.time() - t0:6.1f}s] {m:5.0f} m  voiture {i:2d} P{pos + 1:<2d} tour {lap:2d}  "
                          f"écart {g}  avantage {a}  crédit {max(credit[i], 0) * 100:4.1f} %  {speed * 3.6:3.0f} km/h",
                          flush=True)
            prev[i] = s
        time.sleep(0.05)
    for m, st in stats.items():
        print(f"{m:.0f} m : à moins d'1 s avec avantage {st['proche_a']}, sans {st['proche_sans']} ; "
              f"plus loin avec avantage {st['loin_a']}, sans {st['loin_sans']}")


if __name__ == '__main__':
    main()
