"""Essai en direct : recharge au freinage (RaceSimDataAsset +0x140, ERSBrakingChargeBatteryRate) tenue à une valeur
pendant un temps donné (réécrite toutes les 0,1 s : le script Lua remet sa valeur toutes les 2 s), avec la batterie
de la grille toutes les 30 s. La valeur d'origine est remise à la fin.

  python ersharvest.py <RaceSimDataAsset_hex> <recharge> <secondes>
"""
import ctypes, struct, sys, time
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from monitor import read, find_cfg, STRIDE, GRID, find_pid, k32
from ersbudget import write


def main():
    asset = int(sys.argv[1], 16)
    value = float(sys.argv[2])
    secs = float(sys.argv[3])
    pid = find_pid()
    h = k32.OpenProcess(0x0438, False, pid)
    orig = read(h, asset + 0x140, 4)
    print(f"recharge d'origine {struct.unpack('<f', orig)[0]:.4f}, déploiement "
          f"{struct.unpack('<f', read(h, asset + 0x144, 4))[0]:.4f} -> recharge {value}", flush=True)
    cfg = find_cfg(h, pid)
    last = struct.unpack('<Q', read(h, cfg + 0x58, 8))[0]
    base = last - read(h, last + 0x710, 1)[0] * STRIDE
    packed = struct.pack('<f', value)
    t0 = time.time()
    tick = 0
    acc = [0, 0.0, 0, 0, 0.0, 1.0]  # échantillons, batterie, déploie, sous 25 %, max, min
    try:
        while time.time() - t0 < secs:
            write(h, asset + 0x140, packed)
            if tick % 5 == 0:
                for i in range(GRID):
                    d = read(h, base + i * STRIDE, 0x900)
                    if d is None or d[0x710] != i or struct.unpack_from('<i', d, 0x7E4)[0] < 1:
                        continue
                    b = struct.unpack_from('<f', d, 0x878)[0]
                    acc[0] += 1; acc[1] += b; acc[2] += d[0x874] == 3; acc[3] += b < 0.25
                    acc[4] = max(acc[4], b); acc[5] = min(acc[5], b)
            if tick % 300 == 299 and acc[0]:
                n = acc[0]
                print(f"[{time.time() - t0:5.0f} s] batterie moyenne {acc[1] / n * 100:3.0f} % (min {acc[5] * 100:.0f}, "
                      f"max {acc[4] * 100:.0f}), déploie {acc[2] / n * 100:.0f} %, sous 25 % {acc[3] / n * 100:.0f} %",
                      flush=True)
                acc = [0, 0.0, 0, 0, 0.0, 1.0]
            tick += 1
            time.sleep(0.1)
    finally:
        write(h, asset + 0x140, orig)
        print("recharge d'origine remise", flush=True)


if __name__ == '__main__':
    main()
