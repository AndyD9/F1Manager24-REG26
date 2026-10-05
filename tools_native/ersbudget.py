"""Essai en direct : multiplie le plan de déploiement ERS de l'IA ([[sim+8]+0x6F8], TArray de floats, un par nœud)
et mesure l'effet sur la batterie de la grille. Le plan d'origine est remis à la fin.

  python ersbudget.py <sim8_hex> <facteur> <secondes_avant> <secondes_pendant>

sim8 = [r13+8] de la décision ERS (rbx au point d'arrêt exe+0x230BA2B).
"""
import ctypes, struct, sys, time
from ctypes import wintypes
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from monitor import read, find_cfg, STRIDE, GRID, find_pid, k32

k32.WriteProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
                                   ctypes.POINTER(ctypes.c_size_t)]


def write(h, addr, data):
    buf = ctypes.create_string_buffer(data, len(data))
    return k32.WriteProcessMemory(h, ctypes.c_void_p(addr), buf, len(data), None)


def sample(h, base, secs, label):
    t0 = time.time()
    n = deploy = low = 0
    batt = 0.0
    used = {}
    while time.time() - t0 < secs:
        for i in range(GRID):
            d = read(h, base + i * STRIDE, 0x900)
            if d is None or d[0x710] != i or struct.unpack_from('<i', d, 0x7E4)[0] < 1:
                continue
            b = struct.unpack_from('<f', d, 0x878)[0]
            n += 1
            batt += b
            deploy += d[0x874] == 3
            low += b < 0.25
            used[i] = max(used.get(i, 0.0), struct.unpack_from('<f', d, 0x888)[0])
        time.sleep(0.5)
    if n:
        print(f"{label} : batterie moyenne {batt / n * 100:.0f} %, en déploiement {deploy / n * 100:.0f} % du temps, "
              f"sous 25 % {low / n * 100:.0f} % du temps, déployé max dans un tour {max(used.values()):.2f} batterie",
              flush=True)


def main():
    sim8 = int(sys.argv[1], 16)
    k = float(sys.argv[2])
    before, during = float(sys.argv[3]), float(sys.argv[4])
    pid = find_pid()
    h = k32.OpenProcess(0x0438, False, pid)  # lecture, écriture, opération
    ptr, num = struct.unpack('<Qi', read(h, sim8 + 0x6F8, 12))
    orig = read(h, ptr, num * 4)
    vals = struct.unpack(f'<{num}f', orig)
    print(f"plan {ptr:X}, {num} nœuds, total {max(vals):.3f}")
    cfg = find_cfg(h, pid)
    last = struct.unpack('<Q', read(h, cfg + 0x58, 8))[0]
    base = last - read(h, last + 0x710, 1)[0] * STRIDE
    sample(h, base, before, "plan d'origine")
    if not write(h, ptr, struct.pack(f'<{num}f', *(v * k for v in vals))):
        sys.exit(f"écriture impossible ({ctypes.get_last_error()})")
    print(f"plan × {k} écrit (total {max(vals) * k:.3f})", flush=True)
    try:
        sample(h, base, during, f"plan × {k}")
    finally:
        write(h, ptr, orig)
        print("plan d'origine remis", flush=True)


if __name__ == '__main__':
    main()
