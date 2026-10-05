"""Échantillonne les voitures en Overtake Mode : batterie, état ERS, crédit (g_cfg de Reg2026Patch.dll).

  python monitor.py <objet_voiture_hex> <secondes>
"""
import ctypes, struct, sys, time, re
from ctypes import wintypes
from pathlib import Path

sys.path.insert(0, r"C:\Users\andyd\Documents\DEV\NewReg2026\tools_native")
from inject import find_pid, k32

k32.ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
                                  ctypes.POINTER(ctypes.c_size_t)]
STRIDE = 0x10D8
GRID = 22
LOG = Path(r"F:\SteamLibrary\steamapps\common\F1 Manager 2024\F1Manager24\Binaries\Win64\ue4ss\Mods\Reg2026\patch.log")


def read(h, addr, n):
    buf = ctypes.create_string_buffer(n)
    got = ctypes.c_size_t()
    if not k32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, n, ctypes.byref(got)) or got.value != n:
        return None
    return buf.raw


class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("th32ModuleID", wintypes.DWORD), ("th32ProcessID", wintypes.DWORD),
                ("GlblcntUsage", wintypes.DWORD), ("ProccntUsage", wintypes.DWORD),
                ("modBaseAddr", ctypes.c_void_p), ("modBaseSize", wintypes.DWORD), ("hModule", ctypes.c_void_p),
                ("szModule", wintypes.WCHAR * 256), ("szExePath", wintypes.WCHAR * 260)]


def find_module(pid, name):
    snap = k32.CreateToolhelp32Snapshot(0x18, pid)
    e = MODULEENTRY32W(); e.dwSize = ctypes.sizeof(e)
    ok = k32.Module32FirstW(snap, ctypes.byref(e))
    while ok:
        if e.szModule.lower() == name.lower():
            k32.CloseHandle(snap)
            return e.modBaseAddr, e.modBaseSize
        ok = k32.Module32NextW(snap, ctypes.byref(e))
    k32.CloseHandle(snap)
    return None, None


def find_cfg(h, pid):
    base, size = find_module(pid, "Reg2026Patch.dll")
    if not base:
        return None
    # limites 290 / 337 km/h en +0x24 (la recharge en +0x2C dépend de superclipping.ini) : on vérifie aussi
    # one = 1,0 en +0x54 et step = 1/30 en +0x60
    pat = struct.pack('<ff', 290.0 / 3.6, 337.0 / 3.6)
    img = read(h, base, size)
    if img is None:
        # lire par pages
        img = b''.join((read(h, base + o, 0x1000) or b'\0' * 0x1000) for o in range(0, size, 0x1000))
    i = img.find(pat)
    while i >= 0:
        c = i - 0x24
        if c >= 0 and abs(struct.unpack_from('<f', img, c + 0x54)[0] - 1.0) < 1e-6 and \
                abs(struct.unpack_from('<f', img, c + 0x60)[0] - 1 / 30) < 1e-4:
            return base + c
        i = img.find(pat, i + 1)
    return None


def main():
    car0 = int(sys.argv[1], 16)
    secs = float(sys.argv[2]) if len(sys.argv) > 2 else 60
    pid = find_pid()
    h = k32.OpenProcess(0x0410, False, pid)
    idx0 = read(h, car0 + 0x710, 1)[0]
    base = car0 - idx0 * STRIDE
    cfg = find_cfg(h, pid)
    print(f"base voitures {base:X}, g_cfg {cfg:X}" if cfg else f"base voitures {base:X}, g_cfg introuvable")
    logpos = LOG.stat().st_size
    t0 = time.time()
    last_boost = {}
    stats = {}  # idx -> [samples, deploy, braking, battery_moves]
    prev_batt = {}
    while time.time() - t0 < secs:
        boost = read(h, cfg, 0x20) if cfg else b'\0' * 32
        credit = struct.unpack('<32f', read(h, cfg + 0x64, 128)) if cfg else [0] * 32
        now = time.time() - t0
        for i in range(GRID):
            c = base + i * STRIDE
            d = read(h, c, STRIDE)
            if d is None or d[0x710] != i:
                continue
            batt = struct.unpack_from('<f', d, 0x878)[0]
            state = d[0x874]
            speed = struct.unpack_from('<f', d, 0x198)[0]
            accel = struct.unpack_from('<f', d, 0x19C)[0]
            lap = struct.unpack_from('<i', d, 0x7E4)[0]
            deployed = struct.unpack_from('<f', d, 0x884)[0]
            if boost[i]:
                st = stats.setdefault(i, [0, 0, 0, 0.0])
                st[0] += 1
                st[1] += state == 3
                st[2] += accel < 0
                if i in prev_batt:
                    st[3] += batt - prev_batt[i]
                if not last_boost.get(i):
                    print(f"[{now:6.1f}s] voiture {i:2d} tour {lap} : OVERTAKE début, batterie {batt*100:5.1f}%, crédit {credit[i]*100:5.1f}%")
                print(f"[{now:6.1f}s]   v{i:2d} batt {batt*100:5.1f}% état {state} crédit {credit[i]*100:5.1f}% "
                      f"{speed*3.6:5.0f} km/h acc {accel:+5.1f} déployé/tour {deployed:.2f}")
            elif last_boost.get(i):
                st = stats.get(i, [0, 0, 0, 0.0])
                print(f"[{now:6.1f}s] voiture {i:2d} : OVERTAKE fin, batterie {batt*100:5.1f}% ; {st[0]} échantillons, "
                      f"état déploie {st[1]}, freinage {st[2]}, variation batterie {st[3]*100:+.1f} pt")
                stats.pop(i, None)
            prev_batt[i] = batt
            last_boost[i] = boost[i]
        # journal
        size = LOG.stat().st_size
        if size > logpos:
            with LOG.open('rb') as f:
                f.seek(logpos)
                for line in f.read().decode('utf-8', 'replace').splitlines():
                    print("   LOG", line[11:])
            logpos = size
        time.sleep(0.1)


if __name__ == '__main__':
    main()
