"""Construit zzz_Reg2026UI_P.pak : cases STRAIGHT / OVERTAKE dans le bandeau de chaque pilote (UI Gameface).

Le pak contient tous les fichiers de ui_mod/UIGameface, montés sur F1Manager24/Content/UIGameface.

Usage : python scripts/build_ui.py [--install]
"""
import shutil
import sys
from pathlib import Path

from build_loc import GAME_PAKS, write_pak
from pak_reader import extract, load_index

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "ui_mod" / "UIGameface"
PAK_ROOT = "F1Manager24/Content/UIGameface/"
OUT = ROOT / "build" / "out" / "zzz_Reg2026UI_P.pak"


def main():
    files = {PAK_ROOT + p.relative_to(SRC).as_posix(): p.read_bytes() for p in sorted(SRC.rglob("*")) if p.is_file()}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    write_pak(files, OUT)

    # vérification : on relit le pak produit avec notre lecteur
    f, entries = load_index(OUT)
    for path, data in files.items():
        assert extract(f, entries[path]) == data, path
        print(path)
    f.close()
    print(f"-> {OUT} ({OUT.stat().st_size} o), relu OK")
    if "--install" in sys.argv:
        shutil.copy(OUT, GAME_PAKS / OUT.name)
        print(f"installé dans {GAME_PAKS}")


if __name__ == "__main__":
    main()
