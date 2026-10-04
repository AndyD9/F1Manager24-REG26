"""Lit / réécrit un fichier .locres (UE, versions 2 et 3).

  python scripts/locres.py dump <fichier.locres> <sortie.tsv>
Le TSV contient : namespace, clé, texte (retours à la ligne échappés en \\n).
"""
import struct
import sys

MAGIC = bytes.fromhex("0E147475674A03FC4A15909DC3377F1B")


def read_fstr(b, o):
    n = struct.unpack_from("<i", b, o)[0]; o += 4
    if n == 0:
        return "", o
    if n < 0:
        s = b[o:o - n * 2].decode("utf-16-le")[:-1]
        return s, o - n * 2
    return b[o:o + n].decode("utf-8", "replace")[:-1], o + n


def write_fstr(s):
    if s == "":
        return struct.pack("<i", 1) + b"\0"  # le jeu écrit les chaînes vides ainsi
    if all(ord(c) < 128 for c in s):
        data = s.encode("ascii") + b"\0"
        return struct.pack("<i", len(data)) + data
    data = s.encode("utf-16-le") + b"\0\0"
    return struct.pack("<i", -(len(data) // 2)) + data


class Locres:
    """namespaces : liste de [hash, nom, [[hash, clé, hash source, index chaîne], ...]]"""

    def __init__(self, data):
        b = data
        assert b[:16] == MAGIC, "pas un locres optimisé"
        self.ver = b[16]
        assert self.ver in (2, 3), self.ver
        o = 17
        str_off = struct.unpack_from("<q", b, o)[0]; o += 8
        o += 4  # nombre total d'entrées
        ns_count = struct.unpack_from("<I", b, o)[0]; o += 4
        self.namespaces = []
        for _ in range(ns_count):
            ns_hash = struct.unpack_from("<I", b, o)[0]; o += 4
            ns, o = read_fstr(b, o)
            keys = []
            kc = struct.unpack_from("<I", b, o)[0]; o += 4
            for _ in range(kc):
                k_hash = struct.unpack_from("<I", b, o)[0]; o += 4
                key, o = read_fstr(b, o)
                src_hash, idx = struct.unpack_from("<Ii", b, o); o += 8
                keys.append([k_hash, key, src_hash, idx])
            self.namespaces.append([ns_hash, ns, keys])
        p = str_off
        n = struct.unpack_from("<i", b, p)[0]; p += 4
        self.strings = []
        for _ in range(n):
            s, p = read_fstr(b, p)
            p += 4  # compteur de références
            self.strings.append(s)

    def entries(self):
        for _, ns, keys in self.namespaces:
            for k in keys:
                yield ns, k

    def set_text(self, ns, key, text):
        """Change le texte d'une seule clé (ajoute une chaîne, les autres clés ne bougent pas)."""
        for n, k in self.entries():
            if n == ns and k[1] == key:
                if text in self.strings:
                    k[3] = self.strings.index(text)
                else:
                    self.strings.append(text)
                    k[3] = len(self.strings) - 1
                return
        raise KeyError(f"{ns}/{key}")

    def get_text(self, ns, key):
        for n, k in self.entries():
            if n == ns and k[1] == key:
                return self.strings[k[3]]
        raise KeyError(f"{ns}/{key}")

    def to_bytes(self):
        refs = [0] * len(self.strings)
        for _, k in self.entries():
            refs[k[3]] += 1
        body = bytearray()
        body += struct.pack("<I", sum(len(k) for _, _, k in self.namespaces))
        body += struct.pack("<I", len(self.namespaces))
        for ns_hash, ns, keys in self.namespaces:
            body += struct.pack("<I", ns_hash) + write_fstr(ns) + struct.pack("<I", len(keys))
            for k_hash, key, src_hash, idx in keys:
                body += struct.pack("<I", k_hash) + write_fstr(key) + struct.pack("<Ii", src_hash, idx)
        str_off = 16 + 1 + 8 + len(body)
        strs = bytearray(struct.pack("<i", len(self.strings)))
        for s, r in zip(self.strings, refs):
            strs += write_fstr(s) + struct.pack("<i", r)
        return MAGIC + bytes([self.ver]) + struct.pack("<q", str_off) + bytes(body) + bytes(strs)


if __name__ == "__main__":
    cmd, src = sys.argv[1], sys.argv[2]
    loc = Locres(open(src, "rb").read())
    if cmd == "dump":
        with open(sys.argv[3], "w", encoding="utf-8") as out:
            for ns, (_, key, _, idx) in loc.entries():
                text = loc.strings[idx].replace("\r", "\\r").replace("\n", "\\n")
                out.write(f"{ns}\t{key}\t{text}\n")
        print(f"version {loc.ver}, {sum(1 for _ in loc.entries())} textes, {len(loc.strings)} chaînes")
