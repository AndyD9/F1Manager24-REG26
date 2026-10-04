"""Désassemble une zone du jeu : dans le processus s'il tourne, sinon directement dans F1Manager24.exe
(le code n'est pas chiffré sur le disque).

  python tools_native/disasm.py <rva_hex_debut> <taille_hex> [rva_marque_hex]
"""
import sys

from capstone import CS_ARCH_X86, CS_MODE_64, Cs

BASE = 0x140000000
EXE = r"F:\SteamLibrary\steamapps\common\F1 Manager 2024\F1Manager24\Binaries\Win64\F1Manager24.exe"


def read_code(rva, size):
    try:
        from inject import find_pid, k32, read_mem
        h = k32.OpenProcess(0x0410, False, find_pid())
        code = read_mem(h, BASE + rva, size)
        if code:
            return code
    except SystemExit:
        pass
    import pefile
    pe = pefile.PE(EXE, fast_load=True)
    for s in pe.sections:
        if s.VirtualAddress <= rva < s.VirtualAddress + s.SizeOfRawData:
            with open(EXE, "rb") as f:
                f.seek(rva - s.VirtualAddress + s.PointerToRawData)
                return f.read(size)
    raise ValueError(f"RVA {rva:X} hors des sections")


def main():
    start, size = int(sys.argv[1], 16), int(sys.argv[2], 16)
    mark = int(sys.argv[3], 16) if len(sys.argv) > 3 else None
    code = read_code(start, size)
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    for i in md.disasm(code, BASE + start):
        tag = "   <==" if mark is not None and i.address - BASE == mark else ""
        print(f"{i.address - BASE:8X}  {i.bytes.hex():<22} {i.mnemonic:8} {i.op_str}{tag}")


if __name__ == "__main__":
    main()
