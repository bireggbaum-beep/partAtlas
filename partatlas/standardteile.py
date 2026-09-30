"""
Kaufteil-Katalog: die Normteile, die in 3D-gedruckten Baugruppen immer
wieder vorkommen — Schrauben, Muttern, Scheiben, Gewindeeinsätze,
Magnete, Lager. Beim ersten Start in den Graphen gelegt; der Anwender
kann eigene Kaufteile dazulegen.

Kennungen sind sprechend und stabil (`din912-m3x10`): eine Baugruppe, die
darauf zeigt, zeigt nach einem Update noch auf dasselbe Teil.
"""

LAENGEN = [4, 5, 6, 8, 10, 12, 16, 20, 25, 30, 35, 40]


def _schrauben(norm, bezeichnung, groessen, laengen):
    for m in groessen:
        for l in laengen:
            kennung = f"{norm.lower().replace(' ', '')}-m{str(m).replace('.', '_')}x{str(l).replace('.', '_')}"
            yield kennung, {
                "name": f"{bezeichnung} M{m}×{l}", "kategorie": "Schrauben", "norm": norm,
                "gewinde": f"M{m}", "laenge_mm": l, "einheit": "Stück",
            }


def katalog():
    teile = {}
    teile.update(_schrauben("DIN 912", "Zylinderkopfschraube", [2, 2.5, 3, 4, 5, 6], LAENGEN))
    teile.update(_schrauben("DIN 7991", "Senkkopfschraube", [3, 4, 5], LAENGEN[2:]))
    teile.update(_schrauben("ISO 7380", "Linsenkopfschraube", [3, 4, 5], LAENGEN[2:9]))
    teile.update(_schrauben("DIN 7981", "Blechschraube (für Kunststoff)", [2.2, 2.9], [6.5, 9.5, 13]))
    for m in [2, 2.5, 3, 4, 5, 6, 8]:
        s = str(m).replace(".", "_")
        teile[f"din934-m{s}"] = {"name": f"Sechskantmutter M{m}", "kategorie": "Muttern", "norm": "DIN 934",
                                 "gewinde": f"M{m}", "einheit": "Stück"}
        teile[f"din985-m{s}"] = {"name": f"Sicherungsmutter M{m}", "kategorie": "Muttern", "norm": "DIN 985",
                                 "gewinde": f"M{m}", "einheit": "Stück"}
        teile[f"din125-m{s}"] = {"name": f"Unterlegscheibe M{m}", "kategorie": "Scheiben", "norm": "DIN 125",
                                 "gewinde": f"M{m}", "einheit": "Stück"}
    for m in [3, 4, 5]:
        teile[f"din562-m{m}"] = {"name": f"Vierkantmutter M{m}", "kategorie": "Muttern", "norm": "DIN 562",
                                 "gewinde": f"M{m}", "einheit": "Stück"}
        teile[f"nutenstein-2020-m{m}"] = {"name": f"Nutenstein 2020 M{m}", "kategorie": "Profil & Linear",
                                          "gewinde": f"M{m}", "einheit": "Stück"}
    for m, laengen in [(2, [3, 4]), (2.5, [4]), (3, [4, 5, 5.7, 6]), (4, [6, 8]), (5, [6, 8])]:
        for l in laengen:
            teile[f"einsatz-m{str(m).replace('.', '_')}x{str(l).replace('.', '_')}"] = {
                "name": f"Gewindeeinsatz M{m}×{l} (einschmelzen)", "kategorie": "Gewindeeinsätze",
                "gewinde": f"M{m}", "laenge_mm": l, "einheit": "Stück"}
    for d, h in [(3, 1), (5, 2), (6, 2), (6, 3), (8, 2), (8, 3), (10, 2), (10, 3), (12, 3), (15, 5), (20, 5)]:
        teile[f"magnet-{d}x{h}"] = {"name": f"Neodym-Magnet rund {d}×{h} mm", "kategorie": "Magnete",
                                    "einheit": "Stück"}
    for bez, masse in [("608", "8×22×7"), ("623", "3×10×4"), ("625", "5×16×5"), ("688", "8×16×5"),
                       ("6800", "10×19×5"), ("F623", "3×10×4 mit Bund"), ("LM8UU", "8×15×24 Linear")]:
        teile[f"lager-{bez.lower()}"] = {"name": f"Kugellager {bez} ({masse} mm)", "kategorie": "Lager",
                                         "norm": bez, "einheit": "Stück"}
    for k, d in {
        "gt2-riemen-6mm": ("Zahnriemen GT2 6 mm", "Profil & Linear", "m"),
        "gt2-pulley-20z": ("GT2-Zahnrad 20 Zähne, 5 mm Bohrung", "Profil & Linear", "Stück"),
        "profil-2020": ("Aluprofil 2020", "Profil & Linear", "m"),
        "welle-8mm": ("Welle 8 mm, gehärtet", "Profil & Linear", "m"),
        "zugfeder": ("Zugfeder (Sortiment)", "Kleinteile", "Stück"),
        "druckfeder": ("Druckfeder (Sortiment)", "Kleinteile", "Stück"),
        "gummifuss-10": ("Gummifuss selbstklebend 10 mm", "Kleinteile", "Stück"),
        "kabelbinder-100": ("Kabelbinder 100 mm", "Kleinteile", "Stück"),
        "sekundenkleber": ("Sekundenkleber", "Kleinteile", "Stück"),
        "led-5mm": ("LED 5 mm", "Elektronik", "Stück"),
        "servo-sg90": ("Servo SG90", "Elektronik", "Stück"),
        "motor-nema17": ("Schrittmotor NEMA 17", "Elektronik", "Stück"),
        "luefter-4010": ("Lüfter 40×10 mm", "Elektronik", "Stück"),
        "kabel-jst-xh": ("JST-XH-Stecker (Satz)", "Elektronik", "Stück"),
    }.items():
        teile[k] = {"name": d[0], "kategorie": d[1], "einheit": d[2]}
    for t in teile.values():
        t["standard"] = True
    return teile


KATEGORIEN = ["Schrauben", "Muttern", "Scheiben", "Gewindeeinsätze", "Magnete", "Lager",
              "Profil & Linear", "Elektronik", "Kleinteile", "Eigene"]
