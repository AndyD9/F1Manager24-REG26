"""Plan de déploiement ERS de l'IA : tableau [[sim+8]+0x6F8] (un float par nœud de piste, lu dans exe+0x230BA2B,
comparé à l'énergie déployée par la voiture) et bloc ERS des voitures (+0x874..+0x8A8).

  python ersplan.py <tableau_hex> [nœuds] [secondes]
"""
import struct, sys, time
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from monitor import read, find_cfg, STRIDE, GRID, find_pid, k32


def main():
    table = int(sys.argv[1], 16)
    nodes = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    secs = float(sys.argv[3]) if len(sys.argv) > 3 else 0
    pid = find_pid()
    h = k32.OpenProcess(0x0410, False, pid)
    vals = struct.unpack(f'<{nodes}f', read(h, table, nodes * 4))
    print("plan :", " ".join(f"{i}:{v:.3f}" for i, v in enumerate(vals)))
    cfg = find_cfg(h, pid)
    last = struct.unpack('<Q', read(h, cfg + 0x58, 8))[0]
    base = last - read(h, last + 0x710, 1)[0] * STRIDE
    t0 = time.time()
    while True:
        for i in range(GRID):
            d = read(h, base + i * STRIDE, 0x900)
            if d is None or d[0x710] != i:
                continue
            f = struct.unpack_from('<12f', d, 0x874)
            st = d[0x874]
            lap = struct.unpack_from('<i', d, 0x7E4)[0]
            node = struct.unpack_from('<i', d, 0x1FC)[0]
            print(f"voiture {i:2d} tour {lap:2d} +1FC {node:5d} état {st} batt {f[1]:.3f} débit {f[2]:+.3f} "
                  + " ".join(f"+{0x880 + 4 * k:X} {f[3 + k]:8.3f}" for k in range(9)))
        if time.time() - t0 >= secs:
            break
        print("---")
        time.sleep(1.0)


if __name__ == '__main__':
    main()
