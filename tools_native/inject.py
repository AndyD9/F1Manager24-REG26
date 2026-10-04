"""Charge hwbp.dll dans F1Manager24.exe et analyse le résultat.

  python tools_native/inject.py target <adresse_hex>   -> écrit hwbp_target.txt
  python tools_native/inject.py inject                 -> charge la DLL (attend la fin, ~15 s)
  python tools_native/inject.py show                   -> désassemble chaque instruction trouvée
"""
import ctypes
import os
import sys
import time
from ctypes import wintypes
from pathlib import Path

HERE = Path(__file__).resolve().parent
DLL = HERE / "build" / "hwbp.dll"
TARGET = HERE / "build" / "hwbp_target.txt"
LOG = HERE / "build" / "hwbp_log.txt"
EXE = os.environ.get("HWBP_EXE", "F1Manager24.exe")

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.OpenProcess.restype = wintypes.HANDLE
k32.VirtualAllocEx.restype = ctypes.c_void_p
k32.VirtualAllocEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, wintypes.DWORD]
k32.WriteProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
                                   ctypes.POINTER(ctypes.c_size_t)]
k32.GetProcAddress.restype = ctypes.c_void_p
k32.GetProcAddress.argtypes = [wintypes.HMODULE, ctypes.c_char_p]
k32.GetModuleHandleW.restype = wintypes.HMODULE
k32.CreateRemoteThread.restype = wintypes.HANDLE
k32.CreateRemoteThread.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p,
                                   ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p]


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ProcessID", wintypes.DWORD),
                ("th32DefaultHeapID", ctypes.c_void_p), ("th32ModuleID", wintypes.DWORD),
                ("cntThreads", wintypes.DWORD), ("th32ParentProcessID", wintypes.DWORD),
                ("pcPriClassBase", ctypes.c_long), ("dwFlags", wintypes.DWORD), ("szExeFile", wintypes.WCHAR * 260)]


def find_pid():
    snap = k32.CreateToolhelp32Snapshot(2, 0)
    e = PROCESSENTRY32W()
    e.dwSize = ctypes.sizeof(e)
    # le jeu tourne en deux processus du même nom (petit lanceur + jeu) : on garde celui qui a le plus de threads
    best = None
    ok = k32.Process32FirstW(snap, ctypes.byref(e))
    while ok:
        if e.szExeFile.lower() == EXE.lower() and (best is None or e.cntThreads > best[1]):
            best = (e.th32ProcessID, e.cntThreads)
        ok = k32.Process32NextW(snap, ctypes.byref(e))
    k32.CloseHandle(snap)
    if not best:
        sys.exit(f"{EXE} n'est pas lancé")
    return best[0]


def inject():
    if LOG.exists():
        LOG.unlink()
    pid = find_pid()
    h = k32.OpenProcess(0x1F0FFF, False, pid)
    if not h:
        sys.exit(f"OpenProcess impossible ({ctypes.get_last_error()})")
    path = str(DLL).encode("utf-16-le") + b"\0\0"
    mem = k32.VirtualAllocEx(h, None, len(path), 0x3000, 0x04)
    k32.WriteProcessMemory(h, mem, path, len(path), None)
    load = k32.GetProcAddress(k32.GetModuleHandleW("kernel32.dll"), b"LoadLibraryW")
    t = k32.CreateRemoteThread(h, None, 0, load, mem, 0, None)
    if not t:
        sys.exit(f"CreateRemoteThread impossible ({ctypes.get_last_error()})")
    k32.WaitForSingleObject(t, 10000)
    print(f"DLL chargée dans le processus {pid}, enregistrement en cours…")
    for _ in range(60):
        if LOG.exists():
            time.sleep(0.5)
            print(f"-> {LOG}")
            return
        time.sleep(1)
    print("pas de journal après 60 s")


def show():
    from capstone import CS_ARCH_X86, CS_MODE_64, Cs
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    lines = LOG.read_text().splitlines()
    print(lines[0])
    exe = int(lines[0].split("exe=")[1].split()[0], 16)
    for line in lines[1:]:
        if line.startswith("site"):
            rip = int(line.split("rip=")[1].split()[0], 16)
            print(f"\n=== {line}  (exe+{rip - exe:X})")
        elif line.startswith("regs"):
            print(line)
        elif line.startswith("code"):
            base = int(line.split("base=")[1].split()[0], 16)
            code = bytes.fromhex(line.split()[-1])
            # désassemble depuis plusieurs points de départ pour retomber sur la bonne frontière d'instruction
            for start in range(0xC0, 0x100):
                insns = list(md.disasm(code[start:], base + start))
                if any(i.address == rip for i in insns):
                    break
            for i in insns:
                mark = "  <-- après l'écriture" if i.address == rip else ""
                print(f"  {i.address - exe:9X}  {i.mnemonic:8} {i.op_str}{mark}")
                if i.address > rip + 0x30:
                    break


DEBUG_CARS = Path(r"F:\SteamLibrary\steamapps\common\F1 Manager 2024\F1Manager24\Binaries\Win64\ue4ss\Mods\Reg2026\debug_cars.txt")
ACTOR_SCAN = 0x4000


def read_mem(h, addr, size):
    buf = ctypes.create_string_buffer(size)
    got = ctypes.c_size_t()
    k32.ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
                                      ctypes.POINTER(ctypes.c_size_t)]
    if not k32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, size, ctypes.byref(got)):
        return None
    return buf.raw[:got.value]


def find():
    """Retrouve DRSState dans CarData à partir de debug_cars.txt (touche F11) et écrit la cible."""
    import struct
    rows = [l.split(";") for l in DEBUG_CARS.read_text(encoding="utf-8").splitlines()[1:] if l.strip()]
    h = k32.OpenProcess(0x0410, False, find_pid())  # VM_READ | QUERY_INFORMATION
    cars = []
    for r in rows:
        code, addr, num = r[0], int(r[1], 16), int(r[2])
        if num == 0:
            continue  # voitures modèles (« DRV »), hors course
        mem = read_mem(h, addr, ACTOR_SCAN)
        if not mem:
            print(f"{code} : lecture impossible")
            continue
        cars.append((code, addr, mem, num))
    # les valeurs bougent pendant la course : on cherche un décalage commun où
    #  - DriverNumber (stable) est à sa place,
    #  - l'int32 « RacePos » forme une permutation de 1..N sur toute la grille,
    #  - l'int32 suivant (LapCount) est quasi identique pour tous.
    n = len(cars)
    num_offs = None
    for code, addr, mem, num in cars:
        offs = {o for o in range(0, len(mem) - 4, 4) if struct.unpack_from("<i", mem, o)[0] == num}
        num_offs = offs if num_offs is None else num_offs & offs
    print(f"{n} voitures, DriverNumber possible à : {[hex(o) for o in sorted(num_offs or [])]}")
    common = []
    for o in range(8, ACTOR_SCAN - 8, 4):
        pos = sorted(struct.unpack_from("<i", c[2], o)[0] for c in cars)
        laps = [struct.unpack_from("<i", c[2], o + 4)[0] for c in cars]
        if pos == list(range(1, n + 1)) and max(laps) - min(laps) <= 3 and min(laps) >= 0:
            common.append(o)
    if not common:
        sys.exit("décalage introuvable")
    for o in sorted(common):
        drs = o - 4 - 3  # Gear (int32) juste avant RacePos, DRSState 3 octets avant Gear
        vals = [c[2][drs] for c in cars]
        print(f"RacePos à +0x{o:X} -> DRSState probable à +0x{drs:X}, valeurs : {vals}")
    o = sorted(common)[0]
    target = cars[0][1] + o - 7
    TARGET.write_text(f"{target:X}")
    print(f"cible = {cars[0][0]} +0x{o - 7:X} = {target:X}")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "find":
        find()
    elif cmd == "target":
        TARGET.write_text(sys.argv[2])
        print(f"cible {sys.argv[2]}")
    elif cmd == "inject":
        inject()
    elif cmd == "show":
        show()
