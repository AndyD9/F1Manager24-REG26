"""Suivi passif d'une course : batterie de la grille et dépassements toutes les 30 s.

Batterie moyenne / minimum, part du temps en déploiement et sous 25 % ; places gagnées par une voiture qui avait
l'avantage au dépassement (g_cfg.assist) dans les 4 dernières secondes, ou sans. Rien n'est écrit dans le jeu.

  python race.py <secondes>
"""
import struct, sys, time
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from monitor import read, find_cfg, STRIDE, GRID, find_pid, k32


def main():
    secs = float(sys.argv[1]) if len(sys.argv) > 1 else 300
    pid = find_pid()
    h = k32.OpenProcess(0x0410, False, pid)
    cfg = find_cfg(h, pid)
    if not cfg:
        sys.exit("g_cfg introuvable")
    last = struct.unpack('<Q', read(h, cfg + 0x58, 8))[0]
    base = last - read(h, last + 0x710, 1)[0] * STRIDE
    asset_harvest = struct.unpack('<f', read(h, cfg + 0x2C, 4))[0]
    print(f"g_cfg {cfg:X}, recharge du super clipping {asset_harvest:.5f}", flush=True)
    t0 = time.time()
    acc = [0, 0.0, 0, 0, 1.0]
    gains = {"avec": 0, "sans": 0}
    prevpos, lastassist = {}, {}
    prevuse = bytes(32)
    uses = 0
    episodes, dvs = {}, []
    nxt = 30.0
    while time.time() - t0 < secs:
        now = time.time() - t0
        assist = read(h, cfg + 0xEC, 32)
        use = read(h, cfg, 32)  # g_cfg.boost : Overtake Mode en cours d'utilisation
        credit = struct.unpack('<32f', read(h, cfg + 0x64, 128))
        for i in range(GRID):
            if use[i] and not prevuse[i]:
                uses += 1
                print(f"[{now:4.0f} s] voiture {i:2d} utilise son Overtake Mode (crédit {max(credit[i], 0) * 100:.1f} %)",
                      flush=True)
        prevuse = use
        # écart de vitesse avec la voiture devant pendant l'Overtake Mode (max par utilisation)
        snap = {}
        for i in range(GRID):
            d = read(h, base + i * STRIDE, 0x900)
            if d is not None and d[0x710] == i:
                snap[i] = (struct.unpack_from('<i', d, 0x7E0)[0], struct.unpack_from('<f', d, 0x198)[0] * 3.6,
                           struct.unpack_from('<f', d, 0x878)[0])
        bypos = {p: i for i, (p, _, _) in snap.items()}
        for i in range(GRID):
            if use[i] and i in snap and snap[i][0] - 1 in bypos:
                a = bypos[snap[i][0] - 1]
                dv = snap[i][1] - snap[a][1]
                ep = episodes.setdefault(i, [dv, snap[i][1], snap[a][1], snap[i][2]])
                if dv > ep[0]:
                    ep[:3] = [dv, snap[i][1], snap[a][1]]
            elif not use[i] and i in episodes:
                ep = episodes.pop(i)
                dvs.append(ep[0])
                print(f"[{now:4.0f} s] voiture {i:2d} fin d'utilisation : jusqu'à {ep[0]:+.0f} km/h sur la voiture devant "
                      f"({ep[1]:.0f} contre {ep[2]:.0f}), batterie {ep[3] * 100:.0f} % -> {snap.get(i, (0, 0, 0))[2] * 100:.0f} %",
                      flush=True)
        for i in range(GRID):
            d = read(h, base + i * STRIDE, 0x900)
            if d is None or d[0x710] != i:
                continue
            pos, lap = struct.unpack_from('<ii', d, 0x7E0)
            if lap < 1:
                continue
            b = struct.unpack_from('<f', d, 0x878)[0]
            acc[0] += 1; acc[1] += b; acc[2] += d[0x874] == 3; acc[3] += b < 0.25; acc[4] = min(acc[4], b)
            if assist[i]:
                lastassist[i] = now
            if i in prevpos and 0 <= pos < prevpos[i]:
                gains["avec" if now - lastassist.get(i, -99) < 4 else "sans"] += 1
            if 0 <= pos < GRID:
                prevpos[i] = pos
        if now >= nxt and acc[0]:
            n = acc[0]
            print(f"[{now:4.0f} s] tour {lap:2d} batterie moyenne {acc[1] / n * 100:3.0f} % (min {acc[4] * 100:.0f}), "
                  f"déploie {acc[2] / n * 100:2.0f} %, sous 25 % {acc[3] / n * 100:2.0f} % | places gagnées avec "
                  f"avantage {gains['avec']}, sans {gains['sans']} | utilisations {uses}", flush=True)
            acc = [0, 0.0, 0, 0, 1.0]
            nxt += 30.0
        time.sleep(0.25)
    if dvs:
        dvs.sort()
        print(f"écart de vitesse max par utilisation : médiane {dvs[len(dvs) // 2]:+.0f} km/h, "
              f"de {dvs[0]:+.0f} à {dvs[-1]:+.0f} ({len(dvs)} utilisations)")


if __name__ == '__main__':
    main()
