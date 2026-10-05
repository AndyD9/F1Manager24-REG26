"""Par pas de simulation (distance +0x194 qui change) : batterie, état ERS, débit, crédit des voitures en Overtake.

  python monitor2.py <objet_voiture_hex> <secondes>
"""
import ctypes, struct, sys, time
from ctypes import wintypes
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from monitor import read, find_cfg, STRIDE, GRID, find_pid, k32


def main():
    car0 = int(sys.argv[1], 16)
    secs = float(sys.argv[2]) if len(sys.argv) > 2 else 60
    pid = find_pid()
    h = k32.OpenProcess(0x0410, False, pid)
    idx0 = read(h, car0 + 0x710, 1)[0]
    base = car0 - idx0 * STRIDE
    cfg = find_cfg(h, pid)
    hdr = read(h, cfg, 0x64 + 128)
    print(f"g_cfg {cfg:X} : clipOn {struct.unpack_from('<i', hdr, 0x20)[0]}, limites {struct.unpack_from('<f', hdr, 0x24)[0]*3.6:.0f}/"
          f"{struct.unpack_from('<f', hdr, 0x28)[0]*3.6:.0f} km/h, harvest {struct.unpack_from('<f', hdr, 0x2C)[0]:.4f}, "
          f"step {struct.unpack_from('<f', hdr, 0x60)[0]:.5f}")
    # débit de déploiement de l'asset : r15 du hwbp = BA6A90E0
    asset = int(sys.argv[3], 16) if len(sys.argv) > 3 else None
    if asset:
        a = read(h, asset + 0x140, 8)
        print(f"asset +0x140 (recharge) {struct.unpack_from('<f', a, 0)[0]:.4f}, +0x144 (déploiement) {struct.unpack_from('<f', a, 4)[0]:.4f}")
    t0 = time.time()
    prev = {}
    steps = {}
    while time.time() - t0 < secs:
        hdr = read(h, cfg, 0x64 + 128)
        boost = hdr[:0x20]
        credit = struct.unpack_from('<32f', hdr, 0x64)
        now = time.time() - t0
        for i in range(GRID):
            if not boost[i] and not prev.get(i, (None,))[0]:
                continue
            c = base + i * STRIDE
            d = read(h, c, STRIDE)
            if d is None or d[0x710] != i:
                continue
            dist = struct.unpack_from('<f', d, 0x194)[0]
            batt = struct.unpack_from('<f', d, 0x878)[0]
            rate = struct.unpack_from('<f', d, 0x87C)[0]
            state = d[0x874]
            accel = struct.unpack_from('<f', d, 0x19C)[0]
            speed = struct.unpack_from('<f', d, 0x198)[0]
            lap = struct.unpack_from('<i', d, 0x7E4)[0]
            drslap = struct.unpack_from('<i', d, 0x870)[0]
            p = prev.get(i)
            if p is None or p[1] != dist or bool(p[0]) != bool(boost[i]) or p[2] != credit[i]:
                tag = "DÉBUT" if (p is None or not p[0]) and boost[i] else ("FIN  " if p and p[0] and not boost[i] else "pas  ")
                dd = (dist - p[1]) if p else 0
                print(f"[{now:6.2f}s] v{i:2d} {tag} tour {lap} (drs {drslap}) +{dd:5.1f} m {speed*3.6:4.0f} km/h acc {accel:+5.1f} "
                      f"batt {batt*100:6.2f}% état {state} débit {rate:+.4f} crédit {credit[i]*100:6.2f}%")
                if boost[i]:
                    steps[i] = steps.get(i, 0) + 1
            prev[i] = (boost[i], dist, credit[i])
        time.sleep(0.005)


if __name__ == '__main__':
    main()
