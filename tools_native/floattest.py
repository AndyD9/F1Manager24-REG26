"""Temps au tour avec un float du jeu tenu à une valeur (réécrit toutes les 0,1 s : le script Lua remet ses valeurs
toutes les 2 s), puis remis. Exemple : RaceSimDataAsset +0x13C (ERSAccelerationMultiplier_Inactive).

  python floattest.py <adresse_hex> <valeur> <secondes>
"""
import struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from monitor import read, find_cfg, STRIDE, find_pid, k32
from ersbudget import write
from aerotest import run


def main():
    addr, value, secs = int(sys.argv[1], 16), float(sys.argv[2]), float(sys.argv[3])
    pid = find_pid()
    h = k32.OpenProcess(0x0438, False, pid)
    cfg = find_cfg(h, pid)
    lastcar = struct.unpack('<Q', read(h, cfg + 0x58, 8))[0]
    base = lastcar - read(h, lastcar + 0x710, 1)[0] * STRIDE
    orig = read(h, addr, 4)
    print(f"{addr:X} : {struct.unpack('<f', orig)[0]:.4f} -> {value}", flush=True)
    try:
        run(h, base, secs, f"valeur {value}", [(addr, struct.pack('<f', value))])
    finally:
        write(h, addr, orig)
        print("valeur d'origine remise", flush=True)


if __name__ == '__main__':
    main()
