"""
Läuft IN FreeCAD (FreeCADCmd, ohne Fenster), nicht in partAtlas: wandelt CAD-Dateien in STL um.

partAtlas startet FreeCAD einmal für einen ganzen Stapel (`cad.py`); ein Start kostet Sekunden, zwölf Starte wären
Minuten. Dieses Skript importiert deshalb nichts aus partAtlas — FreeCADs Python kennt es nicht — und nimmt nur die
Standardbibliothek und FreeCADs eigene Module.

Eine STEP-Datei liest `Part.read`; ein FCStd-Dokument wird geöffnet (das lädt es wie beim Doppelklick) und die sichtbaren Körper
werden zu einer Form zusammengefasst.

Auftrag: die JSON-Datei, auf die PARTATLAS_CAD_JOB zeigt:
    {"auftraege": [{"quelle": "...step", "ziel": "...stl"}, ...],
     "abweichung": 0.1, "winkel": 0.5, "ergebnis": "<Pfad der Ergebnisdatei>"}
Ergebnis: je Auftrag zwei Zeilen, sofort geschrieben und geleert — wird FreeCAD beendet, weil eine Datei hängt, weiss
partAtlas aus der letzten Zeile, welche es war:
    {"i": 0, "start": true}
    {"i": 0, "ok": true, "dreiecke": 1234}   oder   {"i": 0, "fehler": "Text"}
Ein Fehler in einer Datei hält den Stapel nicht an.
"""
import json
import os


def _zeile(datei, **werte):
    datei.write(json.dumps(werte) + "\n")
    datei.flush()


def koerper(doc):
    """Die Formen eines FreeCAD-Dokuments, die man als Teil sieht: sichtbar und nicht Bestandteil eines anderen Körpers (Schnitt,
    Body, Vereinigung). Container wie App::Part haben keine Form; ihre Kinder kommen einzeln."""
    formen = []
    for o in doc.Objects:
        if not hasattr(o, "Shape") or not getattr(o, "Visibility", True) or o.Shape.isNull():
            continue
        if any(hasattr(p, "Shape") for p in o.InList):
            continue
        formen.append(o.Shape)
    return formen


def _form(auftrag, part, freecad):
    if not auftrag["quelle"].lower().endswith(".fcstd"):
        return part.read(auftrag["quelle"])
    doc = freecad.openDocument(auftrag["quelle"])
    try:
        formen = koerper(doc)
        if not formen:
            raise ValueError("keine sichtbaren Körper")
        return part.makeCompound(formen)
    finally:
        freecad.closeDocument(doc.Name)


def lauf(job_pfad, part, meshpart, freecad=None):
    """`part`, `meshpart` und `freecad` werden übergeben statt importiert, damit die Suite das Protokoll ohne FreeCAD prüfen kann."""
    with open(job_pfad, encoding="utf-8") as f:
        job = json.load(f)
    with open(job["ergebnis"], "a", encoding="utf-8") as erg:
        for i, auftrag in enumerate(job["auftraege"]):
            _zeile(erg, i=i, start=True)
            try:
                form = _form(auftrag, part, freecad)
                if form.isNull():
                    raise ValueError("leere Form")
                netz = meshpart.meshFromShape(Shape=form, LinearDeflection=job["abweichung"],
                                              AngularDeflection=job["winkel"], Relative=False)
                if netz.CountFacets == 0:
                    raise ValueError("keine Geometrie")
                netz.write(auftrag["ziel"])
                _zeile(erg, i=i, ok=True, dreiecke=netz.CountFacets)
            except Exception as e:           # eine Datei darf scheitern, der Stapel geht weiter
                _zeile(erg, i=i, fehler=f"{type(e).__name__}: {e}")


_job = os.environ.get("PARTATLAS_CAD_JOB")
if _job:
    import FreeCAD
    import MeshPart
    import Part
    lauf(_job, Part, MeshPart, FreeCAD)
