"""Lit les données de piste (RaceSimTrackComponent) directement dans un .uexp de niveau (propriétés non versionnées).

On repère le tableau m_trackNodes, puis on lit à la suite les propriétés du composant dans l'ordre du schéma
(usmap), jusqu'à m_pitNodesCount. Contrôle : m_trackNodesCount + m_pitNodesCount == nombre de points.

  python scripts/track_binary.py <Lvl_X.uexp>
"""
import json
import re
import struct
import sys
from pathlib import Path

VEC, F32, U8, U32, BOOL = "vec", "f32", "u8", "u32", "bool"

TRACK_NODE = [("m_pos", VEC), ("m_maxSpeed", F32), ("m_nodeType", U8), ("m_cornerType", U8),
              ("m_cornerNumber", U8), ("m_dynamicLineOffset", F32), ("m_previousEdgeID", U32),
              ("m_highRiskKerb", BOOL)]
TRACK_POSITION = [("m_trackNodeID", U32), ("m_splineDistance", F32), ("m_offRaceLineDistance", F32)]
EDGE_DATA = [("m_insideEdge", F32), ("m_outsideEdge", F32)]
OFF_TRACK = [("m_insideEdgeOffset", F32), ("m_outsideEdgeOffset", F32), ("m_insideType", U8), ("m_outsideType", U8)]
# en sérialisation non versionnée, les champs propres passent avant ceux du parent (TrackPosition)
TRACK_EDGE = [("m_edgeData", EDGE_DATA), ("m_offTrackData", OFF_TRACK)] + TRACK_POSITION

# propriétés du composant à partir de m_trackNodes (ordre du schéma)
COMPONENT = [("m_trackNodes", ("arr", TRACK_NODE)), ("m_trackEdges", ("arr", TRACK_EDGE)),
             ("m_lastRaceTrackEdgeID", U32)] + \
            [(n, ("arr", TRACK_POSITION)) for n in (
                "m_pitStopPositions", "m_pitLaneRedFlagPositions", "m_garagePositions", "m_carStartPositions",
                "m_DRSDetection", "m_DRSZoneStart", "m_DRSZoneEnd", "m_sectorCheckpoints",
                "m_marshalSectorCheckpoints", "m_safetyCarPositions", "m_pitLaneStartPositions")] + \
            [("m_trackNodesCount", U32), ("m_pitNodesCount", U32)]


class Reader:
    def __init__(self, b, o):
        self.b, self.o = b, o

    def take(self, fmt):
        v = struct.unpack_from(fmt, self.b, self.o)
        self.o += struct.calcsize(fmt)
        return v if len(v) > 1 else v[0]

    def value(self, t):
        if t == VEC:
            return self.take("<ddd")
        if t == F32:
            return self.take("<f")
        if t in (U8, BOOL):
            return self.take("<B")
        if t == U32:
            return self.take("<I")
        if isinstance(t, list):
            return self.struct(t)
        if t[0] == "arr":
            n = self.take("<i")
            if not 0 <= n < 100000:
                raise ValueError(f"tableau de {n} éléments")
            return [self.value(t[1]) for _ in range(n)]
        raise TypeError(t)

    def header(self, nprops):
        """En-tête non versionné -> liste des index de propriétés présentes et non nulles."""
        frags, idx = [], 0
        while True:
            packed = self.take("<H")
            skip, zeroes, last, num = packed & 0x7F, bool(packed & 0x80), bool(packed & 0x100), packed >> 9
            idx += skip
            frags.append((idx, num, zeroes))
            idx += num
            if last:
                break
        if idx > nprops:
            raise ValueError("en-tête invalide")
        nbits = sum(num for _, num, z in frags if z)
        mask = 0
        if nbits:
            if nbits <= 8:
                mask = self.take("<B")
            elif nbits <= 16:
                mask = self.take("<H")
            else:
                for w in range((nbits + 31) // 32):
                    mask |= self.take("<I") << (32 * w)
        present, bit = [], 0
        for start, num, z in frags:
            for i in range(start, start + num):
                if z:
                    if not (mask >> bit) & 1:
                        present.append(i)
                    bit += 1
                else:
                    present.append(i)
        return present

    def struct(self, schema):
        out = {name: 0 for name, _ in schema}
        for i in self.header(len(schema)):
            name, t = schema[i]
            out[name] = self.value(t)
        return out


def plausible_node(n):
    return 0 <= n["m_cornerType"] <= 3 and 0 <= n["m_maxSpeed"] <= 500 and n["m_cornerNumber"] < 40 \
        and all(abs(c) < 1e7 for c in n["m_pos"]) if n["m_pos"] else False


def find_component(b):
    """Cherche le tableau m_trackNodes puis lit les propriétés qui suivent."""
    # candidats : nombre de points (30..2000, int32) suivi d'un en-tête de TrackNode sans saut, marqué
    # « dernier fragment », avec 8 valeurs : octets (0x00|0x80) 0x11
    pattern = re.compile(rb"(?=[\x1e-\xff][\x00-\x07]\x00\x00[\x00\x80]\x11)", re.S)
    for m in pattern.finditer(b):
        o = m.start()
        n = struct.unpack_from("<i", b, o)[0]
        if not 30 <= n <= 2000:
            continue
        r = Reader(b, o)
        try:
            nodes = r.value(("arr", TRACK_NODE))
            if not all(plausible_node(x) for x in nodes):
                continue
            out = {"m_trackNodes": nodes}
            for name, t in COMPONENT[1:-2]:
                # un tableau vide n'est pas écrit : si les deux compteurs de points suivent déjà, on s'arrête
                track, pit = struct.unpack_from("<II", b, r.o)
                if track + pit == len(nodes) and track > pit:
                    out[name] = []
                    continue
                out[name] = r.value(t)
            out["m_trackNodesCount"], out["m_pitNodesCount"] = r.take("<I"), r.take("<I")
        except (ValueError, struct.error, TypeError, IndexError):
            continue
        if out["m_trackNodesCount"] + out["m_pitNodesCount"] == len(nodes):
            out["_offset"] = o
            return out
    raise LookupError("composant de piste introuvable")


if __name__ == "__main__":
    data = Path(sys.argv[1]).read_bytes()
    comp = find_component(data)
    print(json.dumps({k: (v if not isinstance(v, list) or len(v) < 6 else f"[{len(v)} éléments]")
                      for k, v in comp.items()}, indent=1, default=str))
