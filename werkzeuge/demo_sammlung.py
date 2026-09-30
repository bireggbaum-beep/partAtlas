"""
Eine Demo-Sammlung erzeugen: Ordner mit STL, 3MF, OBJ und STEP in
verschiedenen Formen — zum Vorführen und zum Messen.

    python werkzeuge/demo_sammlung.py ZIEL [--anzahl 60]

Mit --anzahl 5700 entsteht eine Sammlung in der Grösse aus dem Konzept
(„Mein Ordner hat 5 700 Einträge“). Fester Samen: zwei Läufe erzeugen
dieselben Dateien.
"""
import argparse
import math
import os
import random
import struct
import zipfile

import numpy as np

WOERTER = {
    "Deko": ["Vase", "Spiralvase", "Teelichthalter", "Stern", "Schale", "Figur", "Ornament", "Blumentopf"],
    "Haushalt": ["Haken", "Wandhaken", "Kabelclip", "Halter", "Deckel", "Seifenschale", "Türstopper", "Klammer"],
    "Technik": ["Zahnrad", "Welle", "Lagerbock", "Adapter", "Gehäuse", "Distanzhülse", "Riemenscheibe", "Flansch"],
    "Werkstatt": ["Kalibrierwürfel", "Bithalter", "Sortierbox", "Werkzeughalter", "Schraubenbox", "Lehre"],
    "Drohne": ["Arm_Front", "Arm_Hinten", "Top_Plate", "Bottom_Plate", "Kamerahalter", "Akkuhalter"],
}
MATERIAL = [("PLA", "#E8E8E8"), ("PETG", "#101010"), ("PLA", "#C0392B"), ("ASA", "#2E86C1"), ("PETG", "#F39C12"), ("TPU", "#27AE60")]


def prisma(poly, hoehe):
    """Senkrechtes Prisma über einem sternförmigen Umriss (Fächer von der Mitte)."""
    p = np.array(poly, np.float32)
    n = len(p)
    unten = np.c_[p, np.zeros(n)]
    oben = np.c_[p, np.full(n, hoehe)]
    mu, mo = np.array([*p.mean(0), 0]), np.array([*p.mean(0), hoehe])
    tri = []
    for i in range(n):
        j = (i + 1) % n
        tri += [(mu, unten[j], unten[i]), (mo, oben[i], oben[j]),
                (unten[i], unten[j], oben[j]), (unten[i], oben[j], oben[i])]
    return np.array(tri, np.float32)


def drehkoerper(profil, segmente=96, drall=0.0):
    """Rotationskörper aus (r, z)-Profil; `drall` verdreht nach oben (Spiralvase)."""
    tri = []
    for k in range(len(profil) - 1):
        (r0, z0), (r1, z1) = profil[k], profil[k + 1]
        for s in range(segmente):
            a0, a1 = 2 * math.pi * s / segmente, 2 * math.pi * (s + 1) / segmente
            d0, d1 = drall * z0, drall * z1
            welle0 = 1 + 0.08 * math.sin(8 * (a0 + d0)) if drall else 1
            welle1 = 1 + 0.08 * math.sin(8 * (a1 + d0)) if drall else 1
            welle2 = 1 + 0.08 * math.sin(8 * (a0 + d1)) if drall else 1
            welle3 = 1 + 0.08 * math.sin(8 * (a1 + d1)) if drall else 1
            p00 = (r0 * welle0 * math.cos(a0), r0 * welle0 * math.sin(a0), z0)
            p01 = (r0 * welle1 * math.cos(a1), r0 * welle1 * math.sin(a1), z0)
            p10 = (r1 * welle2 * math.cos(a0), r1 * welle2 * math.sin(a0), z1)
            p11 = (r1 * welle3 * math.cos(a1), r1 * welle3 * math.sin(a1), z1)
            tri += [(p00, p01, p11), (p00, p11, p10)]
    return np.array(tri, np.float32)


def zahnrad(r, zaehne, dicke):
    pts = []
    for i in range(zaehne * 4):
        a = 2 * math.pi * i / (zaehne * 4)
        rr = r if (i % 4) in (1, 2) else r * 0.82
        pts.append((rr * math.cos(a), rr * math.sin(a)))
    return prisma(pts, dicke)


def stern(r, zacken, dicke):
    return prisma([((r if i % 2 == 0 else r * 0.45) * math.cos(math.pi * i / zacken),
                    (r if i % 2 == 0 else r * 0.45) * math.sin(math.pi * i / zacken)) for i in range(zacken * 2)], dicke)


def quader(x, y, z):
    return prisma([(0, 0), (x, 0), (x, y), (0, y)], z)


def form(rnd, wort):
    s = rnd.uniform(0.6, 2.2)
    wort = wort.lower()
    if "zahnrad" in wort or "riemenscheibe" in wort:
        return zahnrad(20 * s, rnd.randint(12, 40), 6 * s)
    if "stern" in wort or "ornament" in wort:
        return stern(25 * s, rnd.randint(5, 8), 8 * s)
    if "vase" in wort or "blumentopf" in wort or "teelicht" in wort:
        h = 60 * s
        profil = [(0.01, 0), (25 * s, 0.5)] + [(25 * s * (0.8 + 0.35 * math.sin(t / 10 * math.pi)), h * t / 10) for t in range(1, 11)] + [(0.01, h)]
        return drehkoerper(profil, 96, drall=0.03 if "spiral" in wort else 0)
    if "welle" in wort or "hülse" in wort or "flansch" in wort:
        return drehkoerper([(0.01, 0), (8 * s, 0), (8 * s, 40 * s), (0.01, 40 * s)], 48)
    if "schale" in wort:
        return drehkoerper([(0.01, 0), (20 * s, 0), (40 * s, 25 * s), (0.01, 25 * s)], 72)
    if "kalibrier" in wort:
        return quader(20, 20, 20)
    if "arm" in wort or "plate" in wort:
        return quader(rnd.uniform(60, 180), rnd.uniform(15, 90), rnd.uniform(2, 8))
    return quader(rnd.uniform(10, 80) * s, rnd.uniform(10, 60) * s, rnd.uniform(5, 50) * s)


def stl(pfad, netz):
    rec = np.zeros(len(netz), dtype=np.dtype([("n", "<f4", 3), ("e", "<f4", (3, 3)), ("a", "<u2")]))
    rec["e"] = netz
    with open(pfad, "wb") as f:
        f.write(b"partAtlas demo".ljust(80) + struct.pack("<I", len(netz)) + rec.tobytes())


def obj(pfad, netz):
    with open(pfad, "w") as f:
        for t in netz:
            for v in t:
                f.write(f"v {v[0]:.3f} {v[1]:.3f} {v[2]:.3f}\n")
        for i in range(len(netz)):
            f.write(f"f {3 * i + 1} {3 * i + 2} {3 * i + 3}\n")


def dreimf(pfad, netz, rnd, gesliced):
    v = netz.reshape(-1, 3)
    mesh = ("<mesh><vertices>" + "".join(f'<vertex x="{a:.3f}" y="{b:.3f}" z="{c:.3f}"/>' for a, b, c in v)
            + "</vertices><triangles>" + "".join(f'<triangle v1="{3 * i}" v2="{3 * i + 1}" v3="{3 * i + 2}"/>' for i in range(len(netz)))
            + "</triangles></mesh>")
    modell = ('<model unit="millimeter" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
              '<metadata name="Designer">Demo-Werkstatt</metadata>'
              f'<resources><object id="1" type="model">{mesh}</object></resources>'
              '<build><item objectid="1"/></build></model>')
    rels = ('<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
            '</Relationships>')
    with zipfile.ZipFile(pfad, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", modell)
        if gesliced:
            filamente = rnd.sample(MATERIAL, rnd.choice([1, 1, 1, 2, 3]))
            fil = "".join(f'<filament id="{i + 1}" type="{t}" color="{c}" used_m="{rnd.uniform(1, 30):.2f}" used_g="{rnd.uniform(2, 90):.2f}"/>'
                          for i, (t, c) in enumerate(filamente))
            z.writestr("Metadata/slice_info.config",
                       f'<config><plate><metadata key="index" value="1"/><metadata key="prediction" value="{rnd.randint(600, 30000)}"/>'
                       f'<metadata key="weight" value="{rnd.uniform(3, 120):.2f}"/>{fil}</plate></config>')


def step(pfad, titel):
    with open(pfad, "w") as f:
        f.write(f"ISO-10303-21;\nHEADER;\nFILE_NAME('{titel}','2026-09-30',(''),(''),'','','');\nENDSEC;\nEND-ISO-10303-21;\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ziel")
    ap.add_argument("--anzahl", type=int, default=60)
    a = ap.parse_args()
    rnd = random.Random(20260930)
    for i in range(a.anzahl):
        ordner = rnd.choice(list(WOERTER))
        wort = rnd.choice(WOERTER[ordner])
        unter = [ordner] + ([rnd.choice(["Projekt A", "Projekt B", "Remix", "alt"])] if rnd.random() < 0.3 else [])
        pfad_ordner = os.path.join(a.ziel, *unter)
        os.makedirs(pfad_ordner, exist_ok=True)
        name = f"{wort}_{i:04d}" if a.anzahl > 100 else (wort if rnd.random() < 0.6 else f"{wort}_v{rnd.randint(1, 4)}")
        netz = form(rnd, wort)
        art = rnd.random()
        basis = os.path.join(pfad_ordner, name)
        if art < 0.50:
            ziel = basis + ".stl"
            if not os.path.exists(ziel):
                stl(ziel, netz)
        elif art < 0.85:
            ziel = basis + ".3mf"
            if not os.path.exists(ziel):
                dreimf(ziel, netz, rnd, gesliced=rnd.random() < 0.6)
        elif art < 0.95:
            ziel = basis + ".obj"
            if not os.path.exists(ziel):
                obj(ziel, netz)
        else:
            ziel = basis + ".step"
            if not os.path.exists(ziel):
                step(ziel, name)
    print(f"{a.anzahl} Modelle unter {a.ziel}")


if __name__ == "__main__":
    main()
