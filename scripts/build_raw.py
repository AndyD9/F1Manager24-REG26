"""Construit le mod en gardant l'en-tête zen d'origine de chaque fichier du jeu.

retoc to-zen (UE5_1) écrit un en-tête de package différent de celui du moteur
« volta24 » du jeu, ce qui fait planter le jeu au démarrage. Ici on prend le
chunk d'origine (en-tête + données), et on remplace seulement les données par
celles du .uexp modifié (mêmes tailles, seules des valeurs changent).

Usage : python scripts/build_raw.py
"""
import json
import shutil
import struct
import subprocess
from pathlib import Path

from pak_reader import KEY

ROOT = Path(__file__).resolve().parent.parent
RETOC = ROOT / "tools" / "retoc" / "retoc.exe"
AES = "0x" + KEY.hex().upper()  # depuis F1M24_AES_KEY ou aes_key.txt
BASE_PAKS = Path(r"F:\NewReg2026_paks_tmp")
LIST = ROOT / "extract" / "liste_fichiers_jeu.txt"
ORIG_LEGACY = ROOT / "extract" / "legacy"
PATCHED_LEGACY = ROOT / "build" / "mod"
WORK = ROOT / "build" / "raw"
OUT = ROOT / "build" / "out" / "zzz_Reg2026_P.utoc"
# conteneur retoc dont on réutilise l'en-tête de conteneur (même format que les mods qui marchent)
RETOC_BUILD = ROOT / "build" / "retoc_ref" / "zzz_Reg2026_P.utoc"

ASSETS = {
    "RaceSimDataAsset": "RaceSim",
    "DriverTacticsDataAsset": "RaceSim",
    "DRSAccelerationSpeedCurce": "RaceSim",
    "RaceSimAIDataAsset": "RaceSim/AI",
    "CarStatsDataAsset": "SharedAssets/DataAssets",
}


def run(*args):
    subprocess.run([str(a) for a in args], check=True, capture_output=True)


def chunk_info(rel_path):
    """(conteneur, chunk id) du package dans le jeu de base."""
    for line in LIST.read_text(encoding="utf-8").splitlines():
        if line.endswith(f"F1Manager24/Content/{rel_path}.uasset") and "ExportBundleData" in line:
            parts = line.split()
            return parts[0], parts[2]
    raise KeyError(rel_path)


def container_header_id(container):
    for line in LIST.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if parts[0] == container and parts[3] == "ContainerHeader":
            return parts[2]
    raise KeyError(container)


def parse_header(b):
    """-> (offset du bloc store entries, ids, bloc store entries)."""
    n = struct.unpack_from("<I", b, 16)[0]
    ids = [b[20 + i * 8:28 + i * 8] for i in range(n)]
    o = 20 + 8 * n
    blen = struct.unpack_from("<I", b, o)[0]
    return o, ids, b[o + 4:o + 4 + blen]


def store_entry(store, idx):
    """(exports, bundles, [imports]) ; les ArrayView sont relatives à leur propre position."""
    base = idx * 24
    ec, ebc, ic, io_ = struct.unpack_from("<iiII", store, base)
    p = base + 8 + io_
    return ec, ebc, [store[p + i * 8:p + i * 8 + 8] for i in range(ic)]


def rebuild_header(retoc_hdr, base_entries):
    """Remplace les store entries de l'en-tête retoc par celles du jeu (même ordre de packages)."""
    o, ids, store = parse_header(retoc_hdr)
    n = len(ids)
    entries = bytearray(24 * n)
    tail = bytearray()
    for i, pid in enumerate(ids):
        ec, ebc, imports = base_entries[pid]
        field = i * 24 + 8
        offset = (24 * n + len(tail)) - field if imports else 0
        struct.pack_into("<iiIIII", entries, i * 24, ec, ebc, len(imports), offset, 0, 0)
        tail += b"".join(imports)
    new_store = bytes(entries + tail)
    rest = retoc_hdr[o + 4 + len(store):]
    return retoc_hdr[:o] + struct.pack("<I", len(new_store)) + new_store + rest


def main(only=None, keep_orig=False):
    """only : liste d'assets à inclure (tous par défaut) ; keep_orig : ne pas appliquer les modifs (test)."""
    assets = {k: v for k, v in ASSETS.items() if not only or k in only}
    if WORK.exists():
        shutil.rmtree(WORK)
    chunks = WORK / "chunks"
    chunks.mkdir(parents=True)

    # en-tête de conteneur : on fait générer un conteneur complet par retoc et on garde son chunk 06
    stage = WORK / "_stage"
    for name, folder in assets.items():
        dst = stage / "F1Manager24/Content" / folder
        dst.mkdir(parents=True, exist_ok=True)
        for ext in ("uasset", "uexp"):
            shutil.copy(PATCHED_LEGACY / "F1Manager24/Content" / folder / f"{name}.{ext}", dst)
    RETOC_BUILD.parent.mkdir(parents=True, exist_ok=True)
    for f in RETOC_BUILD.parent.glob("zzz_Reg2026_P.*"):
        f.unlink()
    run(RETOC, "to-zen", "--version", "UE5_1", stage, RETOC_BUILD)
    ref = WORK / "_ref"
    run(RETOC, "unpack-raw", RETOC_BUILD, ref)
    manifest = json.loads((ref / "manifest.json").read_text(encoding="utf-8"))
    hdr_file = next(f for f in (ref / "chunks").iterdir() if f.name.endswith("06"))

    base_entries = {}
    for name, folder in assets.items():
        rel = f"{folder}/{name}"
        container, chunk_id = chunk_info(rel)
        base_hdr = WORK / f"_hdr_{container}.bin"
        if not base_hdr.exists():
            run(RETOC, "-a", AES, "get", BASE_PAKS / f"{container}.utoc", container_header_id(container), base_hdr)
        _, ids, store = parse_header(base_hdr.read_bytes())
        pid = bytes.fromhex(chunk_id[:16])
        base_entries[pid] = store_entry(store, ids.index(pid))
        orig_chunk = WORK / f"_orig_{name}.bin"
        run(RETOC, "-a", AES, "get", BASE_PAKS / f"{container}.utoc", chunk_id, orig_chunk)
        data = orig_chunk.read_bytes()
        header_size = int.from_bytes(data[4:8], "little")

        orig_uexp = (ORIG_LEGACY / "F1Manager24/Content" / f"{rel}.uexp").read_bytes()[:-4]
        new_uexp = (PATCHED_LEGACY / "F1Manager24/Content" / f"{rel}.uexp").read_bytes()[:-4]
        assert data[header_size:] == orig_uexp, f"{name}: données d'origine différentes de l'extraction"
        assert len(new_uexp) == len(orig_uexp), f"{name}: taille modifiée"

        if keep_orig:
            new_uexp = orig_uexp
        (chunks / chunk_id).write_bytes(data[:header_size] + new_uexp)
        diff = sum(a != b for a, b in zip(orig_uexp, new_uexp))
        print(f"{name}: chunk {chunk_id}, en-tête {header_size} o, {diff} octets modifiés, "
              f"{len(base_entries[bytes.fromhex(chunk_id[:16])][2])} dépendances")

    (chunks / hdr_file.name).write_bytes(rebuild_header(hdr_file.read_bytes(), base_entries))

    (WORK / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    for f in OUT.parent.glob("zzz_Reg2026_P.*"):
        f.unlink()
    run(RETOC, "pack-raw", WORK, OUT)
    shutil.copy(RETOC_BUILD.with_suffix(".pak"), OUT.with_suffix(".pak"))
    print(f"-> {OUT}")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--only", nargs="*")
    p.add_argument("--orig", action="store_true")
    a = p.parse_args()
    main(a.only, a.orig)
