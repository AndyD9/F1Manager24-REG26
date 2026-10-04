"""Straight Mode réel : supprime la règle « moins d'1 s » du DRS dans le jeu en cours d'exécution.

Fonction exe+0x230C2B0 (machine à états DRS, appelée pour chaque voiture à chaque pas de simulation).
Au passage d'un point de détection, le jeu calcule « temps actuel − temps de passage de la voiture devant »
et saute la détection si l'écart dépasse 1,0 s :

    230C440  movaps xmm0, xmm6
    230C443  subss  xmm0, dword ptr [rbx]
    230C447  comiss xmm0, xmm7          ; xmm7 = 1,0
    230C44A  ja     0x14230c47a         ; 77 2E  <- remplacé par 90 90

Sans ce saut, toute voiture qui passe un point de détection obtient le droit au DRS : le jeu l'ouvre
lui-même dans la zone, avec son vrai gain de vitesse. Les autres conditions du jeu restent : DRS
désactivé les premiers tours, sous voiture de sécurité, drapeaux, piste mouillée.

  python tools_native/patch.py on | off | status
"""
import ctypes
import sys

from inject import find_pid, k32, read_mem

BASE = 0x140000000
SITE = 0x230C44A
ORIGINAL = bytes.fromhex("772E")
PATCHED = bytes.fromhex("9090")
# contexte autour du saut, pour ne jamais écrire ailleurs que prévu
BEFORE = bytes.fromhex("0F2FC7")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    h = k32.OpenProcess(0x0438, False, find_pid())  # VM_OPERATION | VM_READ | VM_WRITE | QUERY_INFORMATION
    addr = BASE + SITE
    ctx = read_mem(h, addr - 3, 5)
    if ctx is None or ctx[:3] != BEFORE or ctx[3:] not in (ORIGINAL, PATCHED):
        sys.exit(f"octets inattendus à exe+{SITE:X} : {ctx.hex() if ctx else None} (autre version du jeu ?)")
    state = "actif" if ctx[3:] == PATCHED else "inactif"
    if cmd == "status":
        print(f"patch {state}")
        return
    new = PATCHED if cmd == "on" else ORIGINAL
    old = ctypes.c_ulong()
    k32.VirtualProtectEx.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_ulong,
                                     ctypes.POINTER(ctypes.c_ulong)]
    if not k32.VirtualProtectEx(h, ctypes.c_void_p(addr), 2, 0x40, ctypes.byref(old)):
        sys.exit(f"VirtualProtectEx impossible ({ctypes.get_last_error()})")
    buf = ctypes.create_string_buffer(new)
    k32.WriteProcessMemory(h, ctypes.c_void_p(addr), buf, 2, None)
    k32.VirtualProtectEx(h, ctypes.c_void_p(addr), 2, old.value, ctypes.byref(old))
    k32.FlushInstructionCache(h, ctypes.c_void_p(addr), 2)
    print(f"patch {'activé' if cmd == 'on' else 'retiré'} (exe+{SITE:X} = {read_mem(h, addr, 2).hex()})")


if __name__ == "__main__":
    main()
