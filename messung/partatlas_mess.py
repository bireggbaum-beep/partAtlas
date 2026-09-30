"""
Einmalige Messung: flatgraph mit dem partAtlas-Datenmodell (Konzept v1.5.0,
§5.1/5.2) bei 50 000 Knoten.

    python partatlas_mess.py bauen  <wurzel>
    python partatlas_mess.py oeffnen <wurzel>      (ein Prozess, eine Stichprobe)
    python partatlas_mess.py abfragen <wurzel>
    python partatlas_mess.py alles <wurzel>

FLATGRAPH_REPO zeigt auf den flatgraphdb-Klon. Kalt misst nur mit root.

Die Mengen sind eine Annahme für eine Sammlung von 10 000 Modellen mit
Druckhistorie, keine Messung eines echten Bestands.
"""
import json
import os
import random
import statistics
import subprocess
import sys
import time

REPO = os.environ.get("FLATGRAPH_REPO", "/home/user/flatgraphdb")
sys.path.insert(0, REPO)

SAMEN = 20260930

MENGEN = {
    "MODEL_ASSET":     10_000,
    "PART_GEOMETRY":   15_000,
    "GCODE_ARTIFACT":   8_000,
    "PRINT_JOB":       16_000,
    "PRINT_PROFILE":      300,
    "MATERIAL_MASTER":    200,
    "MATERIAL_SPOOL":     400,
    "PRINTER_DEVICE":       5,
    "AMS_SLOT":            20,
    "TAG_ITEM":            75,
}
TAGS_JE_MODELL = 3

WOERTER = ("halter clip adapter gehaeuse deckel arm platte ring drohne voron "
           "mount halterung haken box schale zahnrad welle gelenk fuss "
           "kabel fuehrung luefter duese spule kalibrierung").split()
MATERIALIEN = ["PLA", "PETG", "ABS", "ASA", "TPU", "PA-CF"]
FORMATE = [".3mf", ".stl", ".step", ".obj"]
SLICER = ["OrcaSlicer 2.3.0", "Bambu Studio 2.1.1", "PrusaSlicer 2.9.2"]


def rss_kb():
    werte = {}
    with open("/proc/self/status") as f:
        for z in f:
            if z.startswith(("VmRSS", "VmHWM")):
                k, v = z.split(":")
                werte[k] = int(v.split()[0])
    return werte


def text(rnd, n):
    t = []
    while sum(len(w) + 1 for w in t) < n:
        t.append(rnd.choice(WOERTER))
    return " ".join(t)[:n]


def hexhash(rnd):
    return "%064x" % rnd.getrandbits(256)


def kid(art, i):
    return f"{art.lower()[:3]}_{i:06d}"


def bauen(wurzel):
    import flatgraph as fg
    rnd = random.Random(SAMEN)
    db = fg.FlatGraphDB(wurzel)
    t0 = time.perf_counter()
    kanten = 0

    def kante(a, b, art):
        nonlocal kanten
        db.create_edge(a, b, art)
        kanten += 1

    with db.transaction():
        for i in range(MENGEN["PRINTER_DEVICE"]):
            db.create_node("PRINTER_DEVICE", kid("PRINTER_DEVICE", i), {
                "name": ["Voron 2.4", "Bambu P1S", "Prusa MK4", "RatRig V-Core", "Bambu X1C"][i],
                "anschluss": ["moonraker", "bambu_lan", "prusalink", "moonraker", "bambu_lan"][i],
                "host": f"192.168.1.{20 + i}", "bett_mm": [300, 256, 250, 400, 256][i],
                "hoehe_mm": [300, 256, 220, 400, 256][i], "duese_mm": 0.4,
            })
        for i in range(MENGEN["AMS_SLOT"]):
            db.create_node("AMS_SLOT", kid("AMS_SLOT", i), {"name": f"AMS_{i // 4}_Slot_{i % 4 + 1}"})
            kante(f"PRINTER_DEVICE/{kid('PRINTER_DEVICE', i % 5)}", f"AMS_SLOT/{kid('AMS_SLOT', i)}", "HAS_SLOT")
        for i in range(MENGEN["MATERIAL_MASTER"]):
            db.create_node("MATERIAL_MASTER", kid("MATERIAL_MASTER", i), {
                "name": f"Hersteller {i % 20} {rnd.choice(MATERIALIEN)} Farbe {i}",
                "material": rnd.choice(MATERIALIEN), "dichte": 1.24,
            })
        for i in range(MENGEN["MATERIAL_SPOOL"]):
            db.create_node("MATERIAL_SPOOL", kid("MATERIAL_SPOOL", i), {
                "nummer": 9000 + i, "farbe": "#%06x" % rnd.getrandbits(24),
                "charge": f"C{rnd.randrange(10**6):06d}", "rest_g": rnd.uniform(0, 1000),
                "preis_kg": 22.9,
            })
            kante(f"MATERIAL_SPOOL/{kid('MATERIAL_SPOOL', i)}",
                  f"MATERIAL_MASTER/{kid('MATERIAL_MASTER', rnd.randrange(MENGEN['MATERIAL_MASTER']))}", "IS_TYPE_OF")
        for i in range(MENGEN["AMS_SLOT"]):
            kante(f"AMS_SLOT/{kid('AMS_SLOT', i)}", f"MATERIAL_SPOOL/{kid('MATERIAL_SPOOL', i)}", "LOADED_WITH")
        for i in range(MENGEN["PRINT_PROFILE"]):
            db.create_node("PRINT_PROFILE", kid("PRINT_PROFILE", i), {
                "name": f"0.{rnd.choice([12, 16, 20, 28])}mm Profil {i}", "waende": rnd.randint(2, 6),
                "infill": f"{rnd.choice([10, 15, 20, 40])}% {rnd.choice(['Gyroid', 'Grid', 'Cubic'])}",
            })
        for i in range(MENGEN["TAG_ITEM"]):
            db.create_node("TAG_ITEM", kid("TAG_ITEM", i), {"name": f"#tag{i}"})

        teil = 0
        gcode = 0
        for i in range(MENGEN["MODEL_ASSET"]):
            m = f"MODEL_ASSET/{kid('MODEL_ASSET', i)}"
            fmt = rnd.choice(FORMATE)
            name = text(rnd, 24).replace(" ", "_")
            db.create_node("MODEL_ASSET", kid("MODEL_ASSET", i), {
                "name": name,
                "pfad": f"/home/maker/3D-Druck/{text(rnd, 40).replace(' ', '/')}/{name}{fmt}",
                "format": fmt, "bbox_mm": [round(rnd.uniform(5, 300), 1) for _ in range(3)],
                "gewicht_g": round(rnd.uniform(1, 400), 2), "material": rnd.choice(MATERIALIEN),
                "status": rnd.choice(["gedruckt", "nur_geometrie", "in_queue"]),
                "thumbnail": f"thumbs/{hexhash(rnd)[:16]}.png",
                "beschreibung": text(rnd, 200),
            })
            for t in rnd.sample(range(MENGEN["TAG_ITEM"]), TAGS_JE_MODELL):
                kante(m, f"TAG_ITEM/{kid('TAG_ITEM', t)}", "HAS_TAG")
            # 15 000 Teile auf 10 000 Modelle: jedes zweite hat zwei.
            for _ in range(1 + (i % 2)):
                db.create_node("PART_GEOMETRY", kid("PART_GEOMETRY", teil), {
                    "sha256": hexhash(rnd), "datei": f"{name}_teil{teil}.stl",
                    "bbox_mm": [round(rnd.uniform(5, 300), 1) for _ in range(3)],
                    "dreiecke": rnd.randrange(1_000, 2_000_000), "bytes": rnd.randrange(10**4, 10**8),
                })
                kante(m, f"PART_GEOMETRY/{kid('PART_GEOMETRY', teil)}", "HAS_PART")
                teil += 1
            if gcode < MENGEN["GCODE_ARTIFACT"] and i % 5 != 4:
                g = f"GCODE_ARTIFACT/{kid('GCODE_ARTIFACT', gcode)}"
                db.create_node("GCODE_ARTIFACT", kid("GCODE_ARTIFACT", gcode), {
                    "datei": f"storage/gcode/{hexhash(rnd)}.gcode", "sha256": hexhash(rnd),
                    "slicer": rnd.choice(SLICER), "druckzeit_s": rnd.randrange(300, 90_000),
                    "schicht_mm": 0.2, "infill": "15% Gyroid", "duese_c": 220, "bett_c": 60,
                    "filament_g": round(rnd.uniform(1, 400), 2), "filament_mm": round(rnd.uniform(100, 150_000), 1),
                })
                kante(m, g, "HAS_GCODE")
                kante(g, f"PRINT_PROFILE/{kid('PRINT_PROFILE', rnd.randrange(MENGEN['PRINT_PROFILE']))}", "BASED_ON_PROFILE")
                kante(g, f"MATERIAL_MASTER/{kid('MATERIAL_MASTER', rnd.randrange(MENGEN['MATERIAL_MASTER']))}", "REQUIRES_MATERIAL")
                kante(g, f"PRINTER_DEVICE/{kid('PRINTER_DEVICE', rnd.randrange(5))}", "COMPILED_FOR")
                gcode += 1

        for i in range(MENGEN["PRINT_JOB"]):
            beginn = 1_780_000_000 + i * 3_600
            dauer = rnd.randrange(300, 90_000)
            db.create_node("PRINT_JOB", kid("PRINT_JOB", i), {
                "status": rnd.choice(["COMPLETED", "COMPLETED", "COMPLETED", "FAILED", "CANCELLED"]),
                "duration_seconds": dauer, "printer_target": "Klipper_Voron_LAN", "cloud_bypass": True,
                "gcode_file": f"storage/gcode/{hexhash(rnd)}.gcode",
                "tsdb_stream_id": f"printer_stream_{rnd.randrange(10**4)}",
                "tsdb_time_range": [beginn, beginn + dauer], "verbrauch_g": round(rnd.uniform(1, 400), 2),
            })
            j = f"PRINT_JOB/{kid('PRINT_JOB', i)}"
            kante(j, f"GCODE_ARTIFACT/{kid('GCODE_ARTIFACT', rnd.randrange(MENGEN['GCODE_ARTIFACT']))}", "EXECUTED_GCODE")
            kante(j, f"PRINTER_DEVICE/{kid('PRINTER_DEVICE', rnd.randrange(5))}", "EXECUTED_ON")
            kante(j, f"MATERIAL_SPOOL/{kid('MATERIAL_SPOOL', rnd.randrange(MENGEN['MATERIAL_SPOOL']))}", "USED_SPOOL")
        assert teil == MENGEN["PART_GEOMETRY"] and gcode == MENGEN["GCODE_ARTIFACT"], (teil, gcode)
    dauer = time.perf_counter() - t0
    db.close()
    knoten = sum(MENGEN.values())
    return {"knoten": knoten, "kanten": kanten, "aufbau_s": round(dauer, 2)}


def groesse(wurzel):
    gesamt, dateien = 0, 0
    for o, _, ns in os.walk(wurzel):
        for n in ns:
            gesamt += os.path.getsize(os.path.join(o, n))
            dateien += 1
    return {"platte_mb": round(gesamt / 1e6, 1), "dateien": dateien}


def oeffnen_einmal(wurzel):
    """Ein frischer Prozess: Grundlast, Import, Öffnen, Speicher danach."""
    vorher = rss_kb()
    import flatgraph as fg
    nach_import = rss_kb()
    t0 = time.perf_counter()
    db = fg.FlatGraphDB(wurzel)
    t = time.perf_counter() - t0
    nach_oeffnen = rss_kb()
    n = sum(len(db.list_nodes(s, readonly=True)) for s in MENGEN)
    assert n == sum(MENGEN.values()), n
    db.close()
    return {"oeffnen_s": t, "rss_python_mb": vorher["VmRSS"] / 1024,
            "rss_import_mb": nach_import["VmRSS"] / 1024,
            "rss_offen_mb": nach_oeffnen["VmRSS"] / 1024,
            "spitze_mb": nach_oeffnen["VmHWM"] / 1024}


def tracemalloc_einmal(wurzel):
    import tracemalloc
    import flatgraph as fg
    tracemalloc.start()
    db = fg.FlatGraphDB(wurzel)
    aktuell, spitze = tracemalloc.get_traced_memory()
    db.close()
    return {"tracemalloc_mb": aktuell / 1e6, "tracemalloc_spitze_mb": spitze / 1e6}


def median_ms(f, n=15):
    werte = []
    for _ in range(n):
        t0 = time.perf_counter()
        f()
        werte.append((time.perf_counter() - t0) * 1000)
    return round(statistics.median(werte), 3)


def abfragen(wurzel):
    import flatgraph as fg
    db = fg.FlatGraphDB(wurzel)
    r = {}
    m0 = "MODEL_ASSET/" + kid("MODEL_ASSET", 4711)
    wort = "zahnrad"

    # Erste Suche nach dem Öffnen baut den Feldindex; einmal, nicht Median.
    t0 = time.perf_counter()
    treffer = db.find_nodes("MODEL_ASSET", {"name": wort}, readonly=True)
    r["suche_name_erste_ms"] = round((time.perf_counter() - t0) * 1000, 2)
    assert treffer and all(wort in d["name"] for d in treffer.values())
    r["suche_name_treffer"] = len(treffer)
    r["suche_name_warm_ms"] = median_ms(lambda: db.find_nodes("MODEL_ASSET", {"name": wort}, readonly=True))
    t0 = time.perf_counter()
    db.find_nodes("MODEL_ASSET", {"beschreibung": "drohne"}, readonly=True)
    r["suche_beschreibung_erste_ms"] = round((time.perf_counter() - t0) * 1000, 2)
    r["suche_beschreibung_warm_ms"] = median_ms(
        lambda: db.find_nodes("MODEL_ASSET", {"beschreibung": "drohne"}, readonly=True))

    tag = "TAG_ITEM/" + kid("TAG_ITEM", 7)
    mit_tag = db.get_connected(tag, direction="in", rel_type="HAS_TAG")
    assert len(mit_tag) > 100, len(mit_tag)
    r["tag_filter_treffer"] = len(mit_tag)
    r["tag_filter_ms"] = median_ms(lambda: db.get_connected(tag, direction="in", rel_type="HAS_TAG"))

    # Hashtag-Chip plus Suchwort: Schnittmenge zweier Ergebnisse.
    r["tag_und_suche_ms"] = median_ms(lambda: set(db.get_connected(tag, direction="in", rel_type="HAS_TAG"))
                                      & {f"MODEL_ASSET/{k}" for k in db.find_nodes(
                                          "MODEL_ASSET", {"name": wort}, readonly=True)})

    # Bauraum-Prüfung gegen ein 256er-Bett: Prädikat, linearer Lauf.
    passt = lambda b: b is not None and max(b[0], b[1]) <= 256 and b[2] <= 256
    r["bauraum_treffer"] = len(db.find_nodes("MODEL_ASSET", {"bbox_mm": passt}, readonly=True))
    r["bauraum_ms"] = median_ms(lambda: db.find_nodes("MODEL_ASSET", {"bbox_mm": passt}, readonly=True))

    # Grid-Seite: 24 Kacheln aus einer vorsortierten Liste lesen.
    ids = sorted(db.list_nodes("MODEL_ASSET", readonly=True))
    r["grid_seite_24_ms"] = median_ms(lambda: [db.get_node(f"MODEL_ASSET/{k}", readonly=True) for k in ids[5000:5024]])
    r["list_models_readonly_ms"] = median_ms(lambda: db.list_nodes("MODEL_ASSET", readonly=True), 7)
    r["list_models_kopie_ms"] = median_ms(lambda: db.list_nodes("MODEL_ASSET"), 7)

    # Inspector: Modell mit Teilen, Tags, G-Code, Profil, Drucker, Aufträgen.
    def inspector():
        teile = db.get_connected(m0, rel_type="HAS_PART")
        tags = db.get_connected(m0, rel_type="HAS_TAG")
        gcodes = db.get_connected(m0, rel_type="HAS_GCODE")
        jobs = []
        for g in gcodes:
            db.get_connected(g, rel_type="BASED_ON_PROFILE")
            db.get_connected(g, rel_type="COMPILED_FOR")
            jobs += db.get_connected(g, direction="in", rel_type="EXECUTED_GCODE")
        return [db.get_node(x, readonly=True) for x in [m0, *teile, *tags, *gcodes, *jobs]]
    assert len(inspector()) >= 5
    r["inspector_ms"] = median_ms(inspector)

    # „Reicht das Filament?“: Drucker → Slots → Spulen.
    drucker = "PRINTER_DEVICE/" + kid("PRINTER_DEVICE", 0)
    r["ampel_ms"] = median_ms(lambda: [db.get_node(s, readonly=True)["rest_g"]
                                       for s in db.collect_related(drucker, ["HAS_SLOT", "LOADED_WITH"])])

    # Druckprotokoll: alle Aufträge eines Druckers.
    r["protokoll_drucker_treffer"] = len(db.get_connected(drucker, direction="in", rel_type="EXECUTED_ON"))
    r["protokoll_drucker_ms"] = median_ms(lambda: db.get_connected(drucker, direction="in", rel_type="EXECUTED_ON"))

    # Schreiben: ein neues Modell einlesen (Modell, Teil, G-Code, 3 Tags, 4 G-Code-Kanten).
    zaehler = [0]

    def ein_modell():
        i = 900_000 + zaehler[0]
        zaehler[0] += 1
        m = f"MODEL_ASSET/{kid('MODEL_ASSET', i)}"
        g = f"GCODE_ARTIFACT/{kid('GCODE_ARTIFACT', i)}"
        p = f"PART_GEOMETRY/{kid('PART_GEOMETRY', i)}"
        with db.transaction():
            db.create_node("MODEL_ASSET", kid("MODEL_ASSET", i), {"name": f"neu_{i}", "bbox_mm": [1, 2, 3]})
            db.create_node("PART_GEOMETRY", kid("PART_GEOMETRY", i), {"sha256": "0" * 64})
            db.create_node("GCODE_ARTIFACT", kid("GCODE_ARTIFACT", i), {"filament_g": 1.0})
            db.create_edge(m, p, "HAS_PART")
            db.create_edge(m, g, "HAS_GCODE")
            for t in range(3):
                db.create_edge(m, f"TAG_ITEM/{kid('TAG_ITEM', t)}", "HAS_TAG")
            db.create_edge(g, "PRINTER_DEVICE/" + kid("PRINTER_DEVICE", 0), "COMPILED_FOR")
    r["modell_einlesen_ms"] = median_ms(ein_modell, 15)

    # Druckende: Auftrag anlegen, 3 Kanten, Spule abbuchen.
    def druckende():
        i = 900_000 + zaehler[0]
        zaehler[0] += 1
        j = f"PRINT_JOB/{kid('PRINT_JOB', i)}"
        with db.transaction():
            db.create_node("PRINT_JOB", kid("PRINT_JOB", i), {"status": "COMPLETED"})
            db.create_edge(j, "GCODE_ARTIFACT/" + kid("GCODE_ARTIFACT", 1), "EXECUTED_GCODE")
            db.create_edge(j, drucker, "EXECUTED_ON")
            db.create_edge(j, "MATERIAL_SPOOL/" + kid("MATERIAL_SPOOL", 0), "USED_SPOOL")
            db.update_node("MATERIAL_SPOOL", kid("MATERIAL_SPOOL", 0), {"rest_g": 100.0})
    r["druckende_ms"] = median_ms(druckende, 15)

    # Nach einer Änderung dieselbe Namenssuche: der Index wird nachgeführt.
    db.update_node("MODEL_ASSET", kid("MODEL_ASSET", 4711), {"name": "zahnrad_geaendert"})
    r["suche_nach_aenderung_ms"] = median_ms(lambda: db.find_nodes("MODEL_ASSET", {"name": wort}, readonly=True), 1)
    assert kid("MODEL_ASSET", 4711) in db.find_nodes("MODEL_ASSET", {"name": "zahnrad_geaendert"}, readonly=True)
    db.close()
    return r


def kalt():
    os.sync()
    with open("/proc/sys/vm/drop_caches", "w") as f:
        f.write("3\n")


def unterprozess(befehl, wurzel):
    aus = subprocess.run([sys.executable, __file__, befehl, wurzel], capture_output=True, text=True,
                         env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    if aus.returncode:
        raise SystemExit(aus.stderr)
    return json.loads(aus.stdout)


def alles(wurzel):
    import shutil
    if os.path.exists(wurzel):
        shutil.rmtree(wurzel)
    erg = {"bauen": unterprozess("bauen", wurzel)}
    erg["platte"] = groesse(wurzel)
    warm = [unterprozess("oeffnen", wurzel) for _ in range(7)]
    kalte = []
    for _ in range(5):
        kalt()
        kalte.append(unterprozess("oeffnen", wurzel))
    med = lambda l, k: round(statistics.median(x[k] for x in l), 3)
    erg["oeffnen"] = {
        "warm_s": med(warm, "oeffnen_s"), "kalt_s": med(kalte, "oeffnen_s"),
        "rss_nur_python_mb": med(warm, "rss_python_mb"),
        "rss_nach_import_mb": med(warm, "rss_import_mb"),
        "rss_offen_mb": med(warm, "rss_offen_mb"), "rss_spitze_mb": med(warm, "spitze_mb"),
    }
    erg["tracemalloc"] = unterprozess("tracemalloc", wurzel)
    erg["abfragen"] = unterprozess("abfragen", wurzel)
    return erg


if __name__ == "__main__":
    befehl, wurzel = sys.argv[1], sys.argv[2]
    f = {"bauen": bauen, "oeffnen": oeffnen_einmal, "tracemalloc": tracemalloc_einmal,
         "abfragen": abfragen, "alles": alles}[befehl]
    print(json.dumps(f(wurzel), indent=1 if befehl == "alles" else None))
