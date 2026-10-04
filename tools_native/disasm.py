"""Désassemble une zone du jeu en cours d'exécution.

  python tools_native/disasm.py <rva_hex_debut> <taille_hex> [rva_marque_hex]
"""
import sys

from capstone import CS_ARCH_X86, CS_MODE_64, Cs

from inject import find_pid, k32, read_mem

BASE = 0x140000000


def main():
    start, size = int(sys.argv[1], 16), int(sys.argv[2], 16)
    mark = int(sys.argv[3], 16) if len(sys.argv) > 3 else None
    h = k32.OpenProcess(0x0410, False, find_pid())
    code = read_mem(h, BASE + start, size)
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    for i in md.disasm(code, BASE + start):
        tag = "   <==" if mark is not None and i.address - BASE == mark else ""
        print(f"{i.address - BASE:8X}  {i.bytes.hex():<22} {i.mnemonic:8} {i.op_str}{tag}")


if __name__ == "__main__":
    main()
