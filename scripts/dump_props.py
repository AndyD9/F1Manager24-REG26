"""Résume les propriétés d'un JSON UAssetGUI sous forme de lignes chemin = valeur."""
import json
import sys
from pathlib import Path

SKIP = {"$type", "DuplicationIndex", "IsZero", "PropertyTagFlags", "PropertyTagExtensions",
        "PropertyGuid", "ArrayIndex", "Ancestry", "OverrideOperation", "bOverrideOperation"}


def walk(node, path, out):
    if isinstance(node, dict):
        name = node.get("Name")
        here = f"{path}.{name}" if name and "Value" in node else path
        val = node.get("Value")
        if name and "Value" in node and not isinstance(val, (dict, list)):
            out.append(f"{here} = {val}")
            return
        for k, v in node.items():
            if k in SKIP or k == "Name":
                continue
            if k == "Value":
                walk(v, here, out)
            elif isinstance(v, (dict, list)):
                walk(v, here, out)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            walk(v, f"{path}[{i}]", out)


def main(paths):
    for p in paths:
        data = json.loads(Path(p).read_text(encoding="utf-8"))
        out = []
        for i, exp in enumerate(data.get("Exports", [])):
            walk(exp.get("Data", []), f"Export{i}", out)
        print(f"===== {Path(p).stem} ({len(out)} valeurs)")
        print("\n".join(out))


if __name__ == "__main__":
    main(sys.argv[1:])
