"""
Läuft IN FreeCAD (FreeCADCmd, ohne Fenster), nicht in partAtlas: wandelt CAD-Dateien in STL um.

partAtlas startet FreeCAD einmal für einen ganzen Stapel (`cad.py`); ein Start kostet Sekunden, zwölf Starte wären
Minuten. Dieses Skript importiert deshalb nichts aus partAtlas — FreeCADs Python kennt es nicht — und nimmt nur die
Standardbibliothek und FreeCADs eigene Module.

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


def lauf(job_pfad, part, meshpart):
    """`part` und `meshpart` werden übergeben statt importiert, damit die Suite das Protokoll ohne FreeCAD prüfen kann."""
    with open(job_pfad, encoding="utf-8") as f:
        job = json.load(f)
    with open(job["ergebnis"], "a", encoding="utf-8") as erg:
        for i, auftrag in enumerate(job["auftraege"]):
            _zeile(erg, i=i, start=True)
            try:
                form = part.read(auftrag["quelle"])
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
    import MeshPart
    import Part
    lauf(_job, Part, MeshPart)
