"""Construit zzz_Reg2026Loc_P.pak : textes français renommés pour 2026 (Straight Mode / Overtake Mode).

Usage : python scripts/build_loc.py [--install]
"""
import hashlib
import shutil
import struct
import sys
from pathlib import Path

from locres import Locres, write_fstr
from pak_reader import extract, load_index

ROOT = Path(__file__).resolve().parent.parent
GAME_PAKS = Path(r"F:\SteamLibrary\steamapps\common\F1 Manager 2024\F1Manager24\Content\Paks")
LOC_PATH = "F1Manager24/Content/Localization/Volta/fr/Volta.locres"
OUT = ROOT / "build" / "out" / "zzz_Reg2026Loc_P.pak"

# clé -> (texte d'origine attendu, nouveau texte) ; namespace vide
RENAMES = {
    "ERS_OVERTAKE": ("Dépassement", "Overtake Mode"),
    "TEAM_COMMS_TYPE_142": ("Dépassement avec ERS autorisé", "Overtake Mode disponible"),
    "NOTIFICATIONS_DRS_ENABLED": ("DRS activé", "Overtake Mode activé"),  # le jeu ouvre le DRS 2 tours après le départ ou une relance : le Straight Mode est là dès le 1er tour, c'est l'Overtake Mode qui arrive
    "NOTIFICATIONS_DRS_DISABLED": ("DRS désactivé", "Overtake Mode désactivé"),
    "TEAM_COMMS_TYPE_33": ("DRS activé", "Overtake Mode activé"),
    "TEAM_COMMS_TYPE_34": ("DRS désactivé", "Overtake Mode désactivé"),
    "TEAM_COMMS_TYPE_197": ("Voiture derrière avec DRS", "Voiture derrière avec Overtake Mode"),
    "TEAM_COMMS_TYPE_202": ("Voiture derrière sans DRS", "Voiture derrière sans Overtake Mode"),
    "CIRCUIT_INFO_DRS_ZONE": ("Zone DRS", "Zone Straight Mode"),
    "CIRCUIT_INFO_DRS_ACTIVATION": ("Détection DRS", "Détection Overtake"),
    "CIRCUIT_INFO_DETAILS_DESC": ("Aperçu des secteurs, virages et zones DRS de ce circuit.",
                                  "Aperçu des secteurs, virages et zones Straight Mode de ce circuit."),
    "Parts_CarStat_DRS": ("Efficacité du DRS", "Efficacité de l'aéro active"),
    "Part_Stat_DRSDelta": ("Delta DRS", "Delta aéro active"),
    "STAFF_STAT_20": ("Delta DRS", "Delta aéro active"),
    "MAIL_DRSACCELERATION": ("Accélération DRS", "Accélération aéro active"),
    "MAIL_DRSTOPSPEED": ("Vitesse maximale DRS", "Vitesse maximale aéro active"),
}


def write_pak(files, out):
    """Écrit un .pak v11 non compressé, non chiffré. files : {chemin relatif au mount point: bytes}."""
    mount = "../../../"
    body = bytearray()
    encoded = bytearray()
    dirs = {"/": []}
    for path, data in files.items():
        offset = len(body)
        sha = hashlib.sha1(data).digest()
        # FPakEntry v11 devant les données : offset, taille, taille décompressée, compression, hash, flags, taille de bloc
        body += struct.pack("<qqqI", 0, len(data), len(data), 0) + sha + struct.pack("<BI", 0, 0)
        body += data
        enc_off = len(encoded)
        flags = (1 << 31) | (1 << 30) | (1 << 29)  # offset, taille décompressée et taille sur 32 bits
        encoded += struct.pack("<III", flags, offset, len(data))
        d, name = path.rsplit("/", 1)
        parts = d.split("/")
        for i in range(1, len(parts) + 1):
            dirs.setdefault("/".join(parts[:i]) + "/", [])
        dirs[d + "/"].append((name, enc_off))

    fdi = bytearray(struct.pack("<i", len(dirs)))
    for d, entries in dirs.items():
        fdi += write_fstr(d) + struct.pack("<i", len(entries))
        for name, off in entries:
            fdi += write_fstr(name) + struct.pack("<i", off)

    index_off = len(body)
    # l'index principal est suivi de l'index de répertoires complet
    def primary(fdi_off):
        p = bytearray(write_fstr(mount))
        p += struct.pack("<iQ", len(files), 0)
        p += struct.pack("<I", 0)  # pas d'index par hash de chemin
        p += struct.pack("<IQQ", 1, fdi_off, len(fdi)) + hashlib.sha1(fdi).digest()
        p += struct.pack("<i", len(encoded)) + encoded
        p += struct.pack("<i", 0)  # aucune entrée non encodée
        return p

    prim = primary(0)
    fdi_off = index_off + len(prim)
    prim = primary(fdi_off)
    footer = bytes(16) + b"\0" + struct.pack("<IiQQ", 0x5A6F12E1, 11, index_off, len(prim)) + hashlib.sha1(prim).digest()
    footer += bytes(32 * 5)
    out.write_bytes(bytes(body) + bytes(prim) + bytes(fdi) + footer)


def main():
    f, files = load_index(GAME_PAKS / "pakchunk0-Windows.pak")
    loc = Locres(extract(f, files[LOC_PATH]))
    for key, (old, new) in RENAMES.items():
        cur = loc.get_text("", key)
        assert cur == old, f"{key} : « {cur} » au lieu de « {old} »"
        loc.set_text("", key, new)
        print(f"{key}: {old} -> {new}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    write_pak({LOC_PATH: loc.to_bytes()}, OUT)

    # vérification : on relit le pak produit avec notre lecteur
    f2, files2 = load_index(OUT)
    check = Locres(extract(f2, files2[LOC_PATH]))
    assert check.get_text("", "ERS_OVERTAKE") == "Overtake Mode"
    assert check.get_text("", "STAFF_STAT_7") == "Dépassement", "texte partagé modifié par erreur"
    f2.close()
    print(f"-> {OUT} ({OUT.stat().st_size} o), relu OK")
    if "--install" in sys.argv:
        shutil.copy(OUT, GAME_PAKS / OUT.name)
        print(f"installé dans {GAME_PAKS}")


if __name__ == "__main__":
    main()
