"""Temps au tour avec les tableaux aéro d'origine du jeu (CarStatsDataAsset +0x1C0 AeroSpeedMultipliers et +0x200
DirtyAirSpeedMultipliers, doubles ; adresse dans Mods/Reg2026/carstats.txt), réécrits toutes les 0,1 s (la DLL remet
les valeurs 2026 chaque seconde), puis remis. Compare avec les réglages actuels mesurés juste avant.

  python aerotest.py <secondes_avant> <secondes_aero_origine>
"""
import struct, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from monitor import read, find_cfg, STRIDE, GRID, find_pid, k32
from ersbudget import write
from laptimes import fmt

CARSTATS = Path(r"F:\SteamLibrary\steamapps\common\F1 Manager 2024\F1Manager24\Binaries\Win64\ue4ss\Mods\Reg2026\carstats.txt")
AERO_ORIG = (0.831, 0.964, 0.769, 1.0, 0.834, 1.0)   # scripts/patch_2026.py, valeurs d'origine
DIRTY_ORIG = (0.9, 1.0, 0.9, 1.0, 0.9, 1.0)


def run(h, base, secs, label, writes):
    last, laps, t0 = {}, [], time.time()
    while time.time() - t0 < secs:
        for addr, data in writes:
            write(h, addr, data)
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
                last[i] = (lap, None)
        time.sleep(0.1)
    if not laps:
        print(f"{label} : aucun tour complet", flush=True)
        return
    laps.sort()
    med = laps[len(laps) // 2]
    ok = [t for t in laps if t < med * 1.15]
    print(f"{label} : {len(ok)} tours, meilleur {fmt(ok[0])}, médiane {fmt(ok[len(ok) // 2])}", flush=True)


def main():
    before, test = float(sys.argv[1]), float(sys.argv[2])
    pid = find_pid()
    h = k32.OpenProcess(0x0438, False, pid)
    cfg = find_cfg(h, pid)
    lastcar = struct.unpack('<Q', read(h, cfg + 0x58, 8))[0]
    base = lastcar - read(h, lastcar + 0x710, 1)[0] * STRIDE
    obj = int(CARSTATS.read_text().split()[0], 16)
    aero, dirty = read(h, obj + 0x1C0, 48), read(h, obj + 0x200, 48)
    print("aéro actuelle", [round(v, 3) for v in struct.unpack('<6d', aero)], flush=True)
    run(h, base, before, "aéro 2026", [])
    try:
        run(h, base, test, "aéro d'origine", [(obj + 0x1C0, struct.pack('<6d', *AERO_ORIG)),
                                               (obj + 0x200, struct.pack('<6d', *DIRTY_ORIG))])
    finally:
        write(h, obj + 0x1C0, aero)
        write(h, obj + 0x200, dirty)
        print("aéro 2026 remise", flush=True)


if __name__ == '__main__':
    main()
