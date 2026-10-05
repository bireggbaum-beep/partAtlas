"""STEP über FreeCAD: das Protokoll zwischen partAtlas und FreeCADCmd. Echtes FreeCAD gibt es hier nicht; eine Attrappe
führt das echte `cad_skript.py` mit Ersatz für Part und MeshPart aus."""
import json
import os
import sys
import tempfile
import threading
import time

import muster
from muster import check
from partatlas import cad, cad_skript

ATTRAPPE = [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "cad_attrappe.py")]

if __name__ == "__main__":
    tmp = tempfile.mkdtemp()

    # -- Das Skript in FreeCAD: Zeilenprotokoll, ein Fehler hält den Stapel nicht an
    class _Form:
        def isNull(self): return False
    class _Netz:
        CountFacets = 7
        def write(self, ziel): open(ziel, "w").write("stl")
    class _Part:
        @staticmethod
        def read(p):
            if "x" in p: raise RuntimeError("nicht lesbar")
            return _Form()
    class _MeshPart:
        @staticmethod
        def meshFromShape(**kw): return _Netz()
    job = os.path.join(tmp, "job.json")
    erg = os.path.join(tmp, "erg.jsonl")
    json.dump({"auftraege": [{"quelle": "a", "ziel": os.path.join(tmp, "a.stl")}, {"quelle": "x", "ziel": "-"},
                             {"quelle": "b", "ziel": os.path.join(tmp, "b.stl")}],
               "abweichung": 0.1, "winkel": 0.5, "ergebnis": erg}, open(job, "w"))
    cad_skript.lauf(job, _Part, _MeshPart)
    zeilen = [json.loads(z) for z in open(erg).read().splitlines()]
    check("Skript: je Auftrag eine Start- und eine Ergebniszeile, Fehler stehen als Text da",
          [(z["i"], "start" in z, z.get("ok"), "fehler" in z) for z in zeilen] ==
          [(0, True, None, False), (0, False, True, False), (1, True, None, False), (1, False, None, True),
           (2, True, None, False), (2, False, True, False)] and "nicht lesbar" in zeilen[3]["fehler"])
    check("Skript: nach dem Fehler läuft der Stapel weiter (zweite Datei geschrieben)", os.path.exists(os.path.join(tmp, "b.stl")))

    # -- Welche Körper eines FCStd-Dokuments zählen: sichtbar und nicht Teil eines anderen Körpers
    class _Obj:
        def __init__(self, sichtbar=True, form=True, in_liste=()):
            if form:
                self.Shape = _Form()
            self.Visibility, self.InList = sichtbar, list(in_liste)
    sichtbar_a, verdeckt = _Obj(), _Obj(sichtbar=False)
    kind = _Obj()
    schnitt = _Obj()
    kind.InList = [schnitt]                       # steckt in einem Schnitt: zählt nicht einzeln
    container = _Obj(form=False)                  # App::Part: keine Form, aber Kinder verweisen auf ihn
    im_container = _Obj(in_liste=[container])
    class _Dok:
        Objects = [sichtbar_a, verdeckt, kind, schnitt, container, im_container]
    check("Körper: sichtbar und nicht Teil eines anderen Körpers — ein Container verdeckt seine Kinder nicht",
          cad_skript.koerper(_Dok) == [sichtbar_a.Shape, schnitt.Shape, im_container.Shape])

    # -- Welches Programm ist FreeCAD ohne Fenster?
    d = os.path.join(tmp, "bin")
    os.makedirs(d)
    for n in ("freecad", "FreeCADCmd", "prusa-slicer"):
        open(os.path.join(d, n), "w").close()
    check("Konsole: FreeCADCmd neben dem erkannten freecad", cad.konsole_befehl(os.path.join(d, "freecad")) == [os.path.join(d, "FreeCADCmd")])
    check("Konsole: ein Slicer ist kein FreeCAD", cad.konsole_befehl(os.path.join(d, "prusa-slicer")) is None and cad.konsole_befehl(None) is None)
    d2 = os.path.join(tmp, "app")
    os.makedirs(d2)
    appimage = os.path.join(d2, "FreeCAD_1.0.AppImage")
    open(appimage, "w").close()
    check("Konsole: ohne eigene Konsole dieselbe Datei im Konsolenmodus (-c), nie die Oberfläche",
          cad.konsole_befehl(appimage) in ([appimage, "-c"], [cad.shutil.which("freecadcmd") or cad.shutil.which("FreeCADCmd")]))

    # -- Umwandeln: ein Start für den Stapel, Fehler und hängende Dateien betreffen nur sich selbst
    cad.ZEIT_JE_DATEI = 3.0
    cad.START_ZEIT = 30.0
    quelle = os.path.join(tmp, "q")
    os.makedirs(quelle)
    namen = ["gut1.step", "haengt.step", "kaputt.step", "gut2.step"]
    for n in namen + ["langsam.step"]:
        open(os.path.join(quelle, n), "w").write("x")
    ziel = os.path.join(tmp, "ziel")
    os.makedirs(ziel)
    logdatei = os.path.join(tmp, "starts.log")
    os.environ["CAD_ATTRAPPE_LOG"] = logdatei
    t0 = time.time()
    ergebnis = {k: (ok, info) for k, ok, info in cad.umwandeln(
        ATTRAPPE, [(n, os.path.join(quelle, n), os.path.join(ziel, n + ".stl")) for n in namen], threading.Event(),
        os.path.join(tmp, "arbeit"))}
    check("Umwandeln: gute Dateien kommen als Netz, die kaputte als Fehler, die hängende als Zeitgrenze",
          ergebnis["gut1.step"][0] and ergebnis["gut2.step"][0] and ergebnis["gut1.step"][1] == 12
          and not ergebnis["kaputt.step"][0] and "kaputt" in ergebnis["kaputt.step"][1]
          and not ergebnis["haengt.step"][0] and "Zeitgrenze" in ergebnis["haengt.step"][1])
    check("Umwandeln: die Netze liegen da, und die hängende hat die anderen nicht aufgehalten (nach FreeCAD-Neustart)",
          all(os.path.getsize(os.path.join(ziel, n + ".stl")) > 84 for n in ("gut1.step", "gut2.step"))
          and set(ergebnis) == set(namen) and time.time() - t0 < 60)
    check("Umwandeln: ein Start für den Stapel, nach der hängenden Datei genau ein zweiter",
          open(logdatei).read().count("start") == 2)
    check("Umwandeln: der Arbeitsordner wird aufgeräumt", os.listdir(os.path.join(tmp, "arbeit")) == [])

    # -- Schlafmodus: die Wanduhr springt, die Datei in Arbeit darf nicht als hängend gelten
    uhr_echt, sprung = time.time, [0]
    time.time = lambda: uhr_echt() + sprung[0]
    spaeter = threading.Timer(0.5, lambda: sprung.__setitem__(0, 3600))      # eine Stunde Schlaf mitten in „langsam“
    spaeter.start()
    try:
        schlaf = {k: (ok, info) for k, ok, info in cad.umwandeln(
            ATTRAPPE, [(n, os.path.join(quelle, n), os.path.join(ziel, n + "3.stl")) for n in ("langsam.step", "gut1.step")],
            threading.Event(), os.path.join(tmp, "arbeit"))}
    finally:
        spaeter.cancel()
        time.time = uhr_echt
    check("Schlafmodus: springt die Uhr eine Stunde vor, gilt die Datei in Arbeit nicht als hängend (Zeitgrenze zählt Laufzeit, nicht Uhrzeit)",
          set(schlaf) == {"langsam.step", "gut1.step"} and all(ok for ok, _ in schlaf.values()))

    # -- Abbrechen: FreeCAD wird sofort beendet
    stopp = threading.Event()
    t0 = time.time()
    erste = []
    for k, ok, info in cad.umwandeln(ATTRAPPE, [(n, os.path.join(quelle, n), os.path.join(ziel, n + "2.stl"))
                                                for n in ("gut1.step", "haengt.step", "gut2.step")], stopp,
                                     os.path.join(tmp, "arbeit")):
        erste.append(k)
        stopp.set()
    check("Abbrechen: nach dem ersten Ergebnis ist Schluss, ohne auf die hängende Datei zu warten",
          erste == ["gut1.step"] and time.time() - t0 < cad.ZEIT_JE_DATEI + 5 and
          os.listdir(os.path.join(tmp, "arbeit")) == [])

    # -- FreeCAD lässt sich nicht starten
    fehl = list(cad.umwandeln(["/gibt/es/nicht"], [("a", "q", "z"), ("b", "q", "z")], threading.Event(), os.path.join(tmp, "arbeit")))
    check("Programm nicht startbar: jede Datei meldet es, kein Absturz, keine Endlosschleife",
          [(k, ok) for k, ok, _ in fehl] == [("a", False), ("b", False)] and "nicht starten" in fehl[0][2])
    muster.ende()
