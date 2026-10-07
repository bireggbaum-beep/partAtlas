"""Musterdateien für die Suiten: erzeugt, nicht eingecheckt — so ist klar,
was drinsteht und was die Prüfung erwarten darf."""
import faulthandler
import io
import os
import time
import struct
import sys
import zipfile

import numpy as np

# PARTATLAS_QUELLE: eine mutierte Kopie prüfen (Gegenprobe) statt des Repos.
sys.path.insert(0, os.environ.get("PARTATLAS_QUELLE") or os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import warnings
warnings.filterwarnings("ignore", message=".*httpx.*")

PRUEFUNGEN = [0, 0]


def zeitgrenze(sekunden):
    """Eine Suite, die so lange läuft, hängt: sie bricht ab und zeigt den Stapel aller Threads — also die Zeile, an der sie stand.
    Ohne das wartete ein endloser Test (etwa eine Schleife, die auf etwas wartet, das nie kommt) bis zu einer äusseren Zeitgrenze, und
    man erfuhr nach Minuten nur „Terminated“, nicht wo. MUSTER_ZEITGRENZE setzt sie für alle Suiten (Sekunden)."""
    faulthandler.dump_traceback_later(int(os.environ.get("MUSTER_ZEITGRENZE") or sekunden), exit=True)


zeitgrenze(300)       # jede Suite ausser test_ui braucht deutlich unter einer Minute; test_ui setzt sich eine eigene


def check(name, bedingung):
    PRUEFUNGEN[1] += 1
    if bedingung:
        PRUEFUNGEN[0] += 1
        print(f"PASS  {name}")
    else:
        print(f"FAIL  {name}")


def ende():
    ok, n = PRUEFUNGEN
    print(f"\n{ok}/{n} Checks bestanden")
    sys.exit(0 if ok == n else 1)


def quader(x=10, y=20, z=30, versatz=(0, 0, 0)):
    v = np.array([[0, 0, 0], [x, 0, 0], [x, y, 0], [0, y, 0],
                  [0, 0, z], [x, 0, z], [x, y, z], [0, y, z]], np.float32) + np.array(versatz, np.float32)
    f = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4),
         (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
    return v, f


def stl_binaer(pfad, x=10, y=20, z=30, kopf=b"solid auch im binaerkopf"):
    v, f = quader(x, y, z)
    netz = v[np.array(f)]
    rec = np.zeros(len(netz), dtype=np.dtype([("n", "<f4", 3), ("e", "<f4", (3, 3)), ("a", "<u2")]))
    rec["e"] = netz
    with open(pfad, "wb") as fh:
        fh.write(kopf.ljust(80, b" ") + struct.pack("<I", len(netz)) + rec.tobytes())


def stl_ascii(pfad, x=10, y=20, z=30):
    v, f = quader(x, y, z)
    zeilen = ["solid quader"]
    for a, b, c in f:
        zeilen += ["facet normal 0 0 0", " outer loop"]
        zeilen += [f"  vertex {v[i][0]} {v[i][1]} {v[i][2]}" for i in (a, b, c)]
        zeilen += [" endloop", "endfacet"]
    zeilen.append("endsolid quader")
    with open(pfad, "w") as fh:
        fh.write("\n".join(zeilen))


def obj(pfad, x=10, y=20, z=30):
    v, f = quader(x, y, z)
    # Vierecke statt Dreiecke: der Leser muss Vielecke zerlegen.
    vierecke = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    with open(pfad, "w") as fh:
        fh.write("o quader\n")
        fh.writelines(f"v {a} {b} {c}\n" for a, b, c in v)
        fh.writelines("f " + " ".join(f"{i + 1}/1/1" for i in q) + "\n" for q in vierecke)


PNG_1PX = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c6360f8cf00000301010018dd8db40000000049454e44ae426082")


def dreimf(pfad, vorschau=True, slice_info=True, vorschau_als_platte=False):
    """Bambu/Orca-Aufbau: Hauptmodell verweist per p:path auf ein Objekt in
    3D/Objects, mit Verschiebung im Build — zwei Teile, eins versetzt."""
    v, f = quader(10, 10, 10)
    mesh = "<mesh><vertices>" + "".join(f'<vertex x="{a}" y="{b}" z="{c}"/>' for a, b, c in v) + \
           "</vertices><triangles>" + "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in f) + \
           "</triangles></mesh>"
    ns = 'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" ' \
         'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06"'
    objekt = f'<model {ns}><resources><object id="1" type="model">{mesh}</object></resources><build/></model>'
    haupt = (f'<model unit="millimeter" {ns}>'
             '<metadata name="Title">Quader-Paar</metadata><metadata name="Designer">Tester</metadata>'
             '<resources>'
             '<object id="2" type="model"><components><component p:path="/3D/Objects/object_1.model" objectid="1"/></components></object>'
             '<object id="3" type="model"><components><component p:path="/3D/Objects/object_1.model" objectid="1" '
             'transform="1 0 0 0 1 0 0 0 2 0 0 0"/></components></object>'
             '</resources><build>'
             '<item objectid="2" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>'
             '<item objectid="3" transform="1 0 0 0 1 0 0 0 1 20 0 0"/>'
             '</build></model>')
    ziel_bild = "Metadata/plate_1.png" if vorschau_als_platte else "Metadata/thumbnail.png"
    rels = ('<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
            + ('' if vorschau_als_platte else
               f'<Relationship Target="/{ziel_bild}" Id="rel1" '
               'Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/thumbnail"/>')
            + '</Relationships>')
    si = ('<config><plate><metadata key="index" value="1"/><metadata key="prediction" value="3600"/>'
          '<metadata key="weight" value="12.50"/>'
          '<filament id="1" type="PETG" color="#000000" used_m="4.1" used_g="12.5"/></plate>'
          '<plate><metadata key="index" value="2"/><metadata key="weight" value="3.25"/>'
          '<filament id="1" type="PLA" color="#FFFFFF" used_m="1.1" used_g="3.25"/></plate></config>')
    with zipfile.ZipFile(pfad, "w") as z:
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", haupt)
        z.writestr("3D/Objects/object_1.model", objekt)
        if vorschau:
            z.writestr(ziel_bild, PNG_1PX)
        if slice_info:
            z.writestr("Metadata/slice_info.config", si)


def step(pfad):
    with open(pfad, "w") as fh:
        fh.write("ISO-10303-21;\nHEADER;\nFILE_NAME('Welle','2026-09-30',(''),(''),'','','');\nENDSEC;\nEND-ISO-10303-21;\n")


def fcstd(pfad, thumbnail=True, document=True):
    """FreeCAD-Dokument: Zip mit Document.xml (erst die Eigenschaften des Dokuments, dann ein Objekt mit eigenem Label),
    einer BREP-Datei und, wenn verlangt, dem Thumbnail."""
    xml = ('<?xml version="1.0" encoding="utf-8"?><Document SchemaVersion="4"><Properties Count="2">'
           '<Property name="Label" type="App::PropertyString"><String value="Gehaeuse"/></Property>'
           '<Property name="CreatedBy" type="App::PropertyString"><String value="Tester"/></Property></Properties>'
           '<Objects Count="1"><Object type="Part::Box" name="Box"><Properties Count="1">'
           '<Property name="Label" type="App::PropertyString"><String value="Objektlabel"/></Property>'
           '</Properties></Object></Objects></Document>')
    with zipfile.ZipFile(pfad, "w") as z:
        if document:
            z.writestr("Document.xml", xml)
        z.writestr("PartShape.brp", b"DBRep_DrawableShape")
        if thumbnail:
            z.writestr("thumbnails/Thumbnail.png", PNG_1PX)


# -- Arbeitsfunktionen für die Absturz-Prüfungen des Scans (müssen in einem importierbaren Modul liegen: die Arbeiter starten per spawn)
def arbeit_nice(x):
    return os.nice(0)                # die Priorität (nice-Wert) des Arbeiters, wie sie nach dem Start ist


def arbeit_test(x):
    if x == "gift":
        os._exit(1)                  # wie vom Betriebssystem beendet (Speichermangel): kein Fehler, der Prozess ist einfach weg
    if x == "kaputt":
        raise ValueError("kaputt")
    if x == "haengt":
        with open(os.environ["MUSTER_PID_DATEI"], "a") as f:
            f.write(f"{os.getpid()}\n")
        time.sleep(600)              # ein Render, der nie fertig wird
    return x * 2


def arbeit_haengt(*_):
    """Statt `_rendern` (beliebige Argumente): meldet seine PID und wird nie fertig — ein Render, an dem ein Abbruch greifen muss."""
    with open(os.environ["MUSTER_PID_DATEI"], "a") as f:
        f.write(f"{os.getpid()}\n")
    time.sleep(600)
