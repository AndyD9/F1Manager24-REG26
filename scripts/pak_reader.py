"""Lecteur minimal de .pak UE (v11, index chiffré AES) pour lister et extraire des fichiers.

Usage :
  python scripts/pak_reader.py list <fichier.pak> [filtre]
  python scripts/pak_reader.py get <fichier.pak> <chemin dans le pak> <sortie>
"""
import struct
import sys
from Crypto.Cipher import AES

def _load_key():
    """Clé AES du jeu : variable F1M24_AES_KEY ou fichier aes_key.txt à la racine (non versionné)."""
    import os
    from pathlib import Path
    k = os.environ.get("F1M24_AES_KEY")
    if not k:
        f = Path(__file__).resolve().parent.parent / "aes_key.txt"
        if not f.exists():
            sys.exit("Clé AES manquante : définir F1M24_AES_KEY ou créer aes_key.txt (0x...)")
        k = f.read_text().strip()
    return k[2:] if k.lower().startswith("0x") else k


KEY = bytes.fromhex(_load_key())


class Reader:
    def __init__(self, data):
        self.d, self.o = data, 0

    def u32(self):
        v = struct.unpack_from("<I", self.d, self.o)[0]; self.o += 4; return v

    def i32(self):
        v = struct.unpack_from("<i", self.d, self.o)[0]; self.o += 4; return v

    def u64(self):
        v = struct.unpack_from("<Q", self.d, self.o)[0]; self.o += 8; return v

    def raw(self, n):
        v = self.d[self.o:self.o + n]; self.o += n; return v

    def fstr(self):
        n = self.i32()
        if n == 0:
            return ""
        if n < 0:
            return self.raw(-n * 2).decode("utf-16-le")[:-1]
        return self.raw(n).decode("utf-8", "replace")[:-1]


def decrypt(b):
    return AES.new(KEY, AES.MODE_ECB).decrypt(b)


def read_at(f, off, size, encrypted=True):
    f.seek(off)
    if encrypted:
        size = (size + 15) // 16 * 16
    b = f.read(size)
    return decrypt(b) if encrypted else b


def load_index(path):
    f = open(path, "rb")
    f.seek(-221, 2)
    foot = f.read(221)
    enc_index = foot[16]
    magic, ver, idx_off, idx_size = struct.unpack_from("<IiQQ", foot, 17)
    assert magic == 0x5A6F12E1 and ver == 11, (hex(magic), ver)
    r = Reader(read_at(f, idx_off, idx_size, enc_index))
    mount = r.fstr()
    r.i32()  # NumEntries
    r.u64()  # PathHashSeed
    if r.u32():
        r.u64(); r.u64(); r.raw(20)
    assert r.u32(), "pas d'index de répertoires complet"
    fdi_off, fdi_size = r.u64(), r.u64(); r.raw(20)
    enc_entries = r.raw(r.i32())
    fdi = Reader(read_at(f, fdi_off, fdi_size, enc_index))
    files = {}
    for _ in range(fdi.i32()):
        d = fdi.fstr()
        for _ in range(fdi.i32()):
            name = fdi.fstr()
            files[(mount + d + name).replace("../../../", "")] = decode_entry(enc_entries, fdi.i32())
    return f, files


def decode_entry(blob, off):
    r = Reader(blob); r.o = off
    v = r.u32()
    bs = (v & 0x3F) << 11
    if (v & 0x3F) == 0x3F:
        bs = r.u32()
    nblocks = (v >> 6) & 0xFFFF
    encrypted = bool((v >> 22) & 1)
    comp = (v >> 23) & 0x3F
    offset = r.u32() if (v >> 31) & 1 else r.u64()
    usize = r.u32() if (v >> 30) & 1 else r.u64()
    size = usize
    if comp:
        size = r.u32() if (v >> 29) & 1 else r.u64()
    blocks = []
    if nblocks > 1 or (nblocks == 1 and encrypted):
        blocks = [r.u32() for _ in range(nblocks)]
    return dict(offset=offset, size=size, usize=usize, comp=comp, enc=encrypted, nblocks=nblocks, blocks=blocks,
                block_size=bs)


def header_size(e):
    # FPakEntry v11 sérialisé devant les données
    return 53 + (4 + 16 * e["nblocks"] if e["comp"] else 0)


_oodle = None


def oodle_decompress(src, usize):
    global _oodle
    if _oodle is None:
        import ctypes
        from pathlib import Path
        dll = Path(__file__).resolve().parent.parent / "tools" / "retoc" / "oo2core_9_win64.dll"
        _oodle = ctypes.WinDLL(str(dll))
        _oodle.OodleLZ_Decompress.restype = ctypes.c_int64
        _oodle.OodleLZ_Decompress.argtypes = [ctypes.c_char_p, ctypes.c_int64, ctypes.c_char_p, ctypes.c_int64] + \
            [ctypes.c_int] * 3 + [ctypes.c_void_p, ctypes.c_int64, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                                  ctypes.c_int64, ctypes.c_int]
    import ctypes
    out = ctypes.create_string_buffer(usize)
    n = _oodle.OodleLZ_Decompress(src, len(src), out, usize, 1, 0, 0, None, 0, None, None, None, 0, 3)
    assert n == usize, f"Oodle : {n} au lieu de {usize}"
    return out.raw


def extract(f, e):
    start = e["offset"] + header_size(e)
    if not e["comp"]:
        return read_at(f, start, e["size"], e["enc"])[:e["size"]]
    sizes = e["blocks"] or [e["size"]]
    out, pos, left = bytearray(), start, e["usize"]
    bs = e.get("block_size") or e["usize"]
    for s in sizes:
        raw = read_at(f, pos, s, e["enc"])[:s]
        pos += (s + 15) // 16 * 16 if e["enc"] else s
        chunk = min(bs, left)
        out += oodle_decompress(raw, chunk)
        left -= chunk
    return bytes(out)


if __name__ == "__main__":
    cmd, pak = sys.argv[1], sys.argv[2]
    f, files = load_index(pak)
    if cmd == "list":
        flt = sys.argv[3].lower() if len(sys.argv) > 3 else ""
        for p, e in sorted(files.items()):
            if flt in p.lower():
                print(f"{p}\tcomp={e['comp']} enc={e['enc']} size={e['size']} usize={e['usize']}")
    elif cmd == "get":
        open(sys.argv[4], "wb").write(extract(f, files[sys.argv[3]]))
