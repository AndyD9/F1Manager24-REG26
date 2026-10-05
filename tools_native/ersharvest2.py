"""Essai en direct : recharge au freinage (RaceSimDataAsset +0x140) et recharge du super clipping (g_cfg.harvest,
+0x2C) tenues à des valeurs données, limite de vitesse gardée. Réécrites toutes les 0,1 s (le script Lua remet la
recharge toutes les 2 s, la DLL g_cfg.harvest chaque seconde), remises à la fin. Batterie de la grille toutes les 30 s.

  python ersharvest2.py <RaceSimDataAsset_hex> <recharge_freinage> <recharge_clipping> <secondes>
"""
import struct, sys, time
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from monitor import read, find_cfg, STRIDE, GRID, find_pid, k32
from ersbudget import write


def main():
    asset = int(sys.argv[1], 16)
    brake, clip, secs = float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
    pid = find_pid()
    h = k32.OpenProcess(0x0438, False, pid)
    cfg = find_cfg(h, pid)
    orig_brake, orig_clip = read(h, asset + 0x140, 4), read(h, cfg + 0x2C, 4)
    print(f"freinage {struct.unpack('<f', orig_brake)[0]:.4f} -> {brake}, clipping "
          f"{struct.unpack('<f', orig_clip)[0]:.5f} -> {clip}", flush=True)
    last = struct.unpack('<Q', read(h, cfg + 0x58, 8))[0]
    base = last - read(h, last + 0x710, 1)[0] * STRIDE
    t0, tick = time.time(), 0
    acc = [0, 0.0, 0, 0, 1.0]
    try:
        while time.time() - t0 < secs:
            write(h, asset + 0x140, struct.pack('<f', brake))
            write(h, cfg + 0x2C, struct.pack('<f', clip))
            if tick % 5 == 0:
                for i in range(GRID):
                    d = read(h, base + i * STRIDE, 0x900)
                    if d is None or d[0x710] != i or struct.unpack_from('<i', d, 0x7E4)[0] < 1:
                        continue
                    b = struct.unpack_from('<f', d, 0x878)[0]
                    acc[0] += 1; acc[1] += b; acc[2] += d[0x874] == 3; acc[3] += b < 0.25; acc[4] = min(acc[4], b)
            if tick % 300 == 299 and acc[0]:
                n = acc[0]
                print(f"[{time.time() - t0:5.0f} s] batterie moyenne {acc[1] / n * 100:3.0f} % (min {acc[4] * 100:.0f}), "
                      f"déploie {acc[2] / n * 100:.0f} %, sous 25 % {acc[3] / n * 100:.0f} %", flush=True)
                acc = [0, 0.0, 0, 0, 1.0]
            tick += 1
            time.sleep(0.1)
    finally:
        write(h, asset + 0x140, orig_brake)
        write(h, cfg + 0x2C, orig_clip)
        print("valeurs d'origine remises", flush=True)


if __name__ == '__main__':
    main()
