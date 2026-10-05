"""Essai en direct combiné : sans limite de vitesse de déploiement (g_cfg.clipOn = 0), plan de déploiement de l'IA
multiplié, recharge au freinage changée. Tout est réécrit toutes les 0,1 s (la DLL remet clipOn chaque seconde, le
script Lua la recharge toutes les 2 s) puis remis à la fin. Batterie de la grille toutes les 30 s.

  python erscombo.py <sim8_hex> <RaceSimDataAsset_hex> <facteur_plan> <recharge> <secondes>
"""
import struct, sys, time
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from monitor import read, find_cfg, STRIDE, GRID, find_pid, k32
from ersbudget import write


def main():
    sim8, asset = int(sys.argv[1], 16), int(sys.argv[2], 16)
    k, value, secs = float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5])
    pid = find_pid()
    h = k32.OpenProcess(0x0438, False, pid)
    cfg = find_cfg(h, pid)
    ptr, num = struct.unpack('<Qi', read(h, sim8 + 0x6F8, 12))
    plan = read(h, ptr, num * 4)
    scaled = struct.pack(f'<{num}f', *(v * k for v in struct.unpack(f'<{num}f', plan)))
    harvest = read(h, asset + 0x140, 4)
    clip = read(h, cfg + 0x20, 4)
    last = struct.unpack('<Q', read(h, cfg + 0x58, 8))[0]
    base = last - read(h, last + 0x710, 1)[0] * STRIDE
    print(f"sans limite, plan × {k}, recharge {value}", flush=True)
    write(h, ptr, scaled)
    t0, tick = time.time(), 0
    acc = [0, 0.0, 0, 0, 1.0, 0.0]  # échantillons, batterie, déploie, sous 25 %, min, déployé max dans le tour
    try:
        while time.time() - t0 < secs:
            write(h, cfg + 0x20, b'\0\0\0\0')
            write(h, asset + 0x140, struct.pack('<f', value))
            if tick % 5 == 0:
                for i in range(GRID):
                    d = read(h, base + i * STRIDE, 0x900)
                    if d is None or d[0x710] != i or struct.unpack_from('<i', d, 0x7E4)[0] < 1:
                        continue
                    b = struct.unpack_from('<f', d, 0x878)[0]
                    acc[0] += 1; acc[1] += b; acc[2] += d[0x874] == 3; acc[3] += b < 0.25
                    acc[4] = min(acc[4], b); acc[5] = max(acc[5], struct.unpack_from('<f', d, 0x888)[0])
            if tick % 300 == 299 and acc[0]:
                n = acc[0]
                print(f"[{time.time() - t0:5.0f} s] batterie moyenne {acc[1] / n * 100:3.0f} % (min {acc[4] * 100:.0f}), "
                      f"déploie {acc[2] / n * 100:.0f} %, sous 25 % {acc[3] / n * 100:.0f} %, "
                      f"déployé max dans un tour {acc[5]:.2f}", flush=True)
                acc = [0, 0.0, 0, 0, 1.0, 0.0]
            tick += 1
            time.sleep(0.1)
    finally:
        write(h, ptr, plan)
        write(h, asset + 0x140, harvest)
        write(h, cfg + 0x20, clip)
        print("valeurs d'origine remises", flush=True)


if __name__ == '__main__':
    main()
