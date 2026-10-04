"""Lit un fichier .usmap (version 4, non compressé) et affiche classes/structs et leurs champs.

  python scripts/usmap.py <Mappings.usmap> struct <Nom>      -> champs d'un struct/classe
  python scripts/usmap.py <Mappings.usmap> find <motif>      -> structs ayant un champ qui contient le motif
  python scripts/usmap.py <Mappings.usmap> enum <Nom>        -> valeurs d'une enum
"""
import struct
import sys

TYPES = ["Byte", "Bool", "Int", "Float", "Object", "Name", "Delegate", "Double", "Array", "Struct", "Str",
         "Text", "Interface", "MulticastDelegate", "WeakObject", "LazyObject", "AssetObject", "SoftObject",
         "UInt64", "UInt32", "UInt16", "Int64", "Int16", "Int8", "Map", "Set", "Enum", "FieldPath", "Optional",
         "Utf8Str", "AnsiStr"]


class R:
    def __init__(self, b, o):
        self.b, self.o = b, o

    def f(self, fmt):
        v = struct.unpack_from(fmt, self.b, self.o)
        self.o += struct.calcsize(fmt)
        return v[0]


def load(path):
    b = open(path, "rb").read()
    r = R(b, 0)
    assert r.f("<H") == 0x30C4
    ver = r.f("<B")
    if ver >= 1 and r.f("<i"):
        raise NotImplementedError("versioning")
    assert r.f("<B") == 0, "usmap compressé"
    r.f("<I"); r.f("<I")
    names = []
    for _ in range(r.f("<I")):
        n = r.f("<H") if ver >= 2 else r.f("<B")
        names.append(b[r.o:r.o + n].decode("utf-8", "replace")); r.o += n
    enums = {}
    for _ in range(r.f("<I")):
        en = names[r.f("<I")]
        cnt = r.f("<H") if ver >= 3 else r.f("<B")
        vals = []
        for i in range(cnt):
            if ver >= 4:
                v = r.f("<Q"); vals.append((v, names[r.f("<I")]))
            else:
                vals.append((i, names[r.f("<I")]))
        enums[en] = vals

    def ptype():
        t = TYPES[r.f("<B")]
        if t == "Struct":
            return f"Struct<{names[r.f('<I')]}>"
        if t == "Enum":
            inner = ptype()
            return f"Enum<{names[r.f('<I')]}:{inner}>"
        if t in ("Array", "Set", "Optional"):
            return f"{t}<{ptype()}>"
        if t == "Map":
            k = ptype()
            return f"Map<{k},{ptype()}>"
        return t

    structs = {}
    for _ in range(r.f("<I")):
        sn = names[r.f("<I")]
        sup = r.f("<I")
        sup = None if sup == 0xFFFFFFFF else names[sup]
        r.f("<H")
        props = []
        for _ in range(r.f("<H")):
            r.f("<H"); dim = r.f("<B")
            pn = names[r.f("<I")]
            props.append((pn, ptype(), dim))
        structs[sn] = (sup, props)
    return enums, structs


if __name__ == "__main__":
    enums, structs = load(sys.argv[1])
    cmd, arg = sys.argv[2], sys.argv[3]
    if cmd == "struct":
        name = arg
        while name:
            sup, props = structs[name]
            print(f"== {name} (parent: {sup})")
            for p in props:
                print(f"   {p[0]}: {p[1]}" + (f" [{p[2]}]" if p[2] > 1 else ""))
            name = sup
    elif cmd == "find":
        for sn, (sup, props) in structs.items():
            hits = [p for p in props if arg.lower() in p[0].lower()]
            if hits:
                print(sn, "->", ", ".join(f"{p[0]}:{p[1]}" for p in hits))
    elif cmd == "enum":
        for v, n in enums[arg]:
            print(v, n)
