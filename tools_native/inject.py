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
    ok = k32.Process32FirstW(snap, ctypes.byref(e))
    while ok:
        if e.szExeFile.lower() == EXE.lower():
            k32.CloseHandle(snap)
            return e.th32ProcessID
        ok = k32.Process32NextW(snap, ctypes.byref(e))
    k32.CloseHandle(snap)
    sys.exit(f"{EXE} n'est pas lancé")


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


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "target":
        TARGET.write_text(sys.argv[2])
        print(f"cible {sys.argv[2]}")
    elif cmd == "inject":
        inject()
    elif cmd == "show":
        show()
