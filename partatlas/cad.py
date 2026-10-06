"""
CAD-Dateien über FreeCAD in ein Netz umwandeln (STEP: Maße, Vorschau, 3D-Ansicht).

partAtlas bringt kein Open CASCADE mit — das macht eine Anwendung um ein Vielfaches grösser (der 3MF Katalog mit
STEP-Vorschau ist fast viermal so gross wie ohne). Wer FreeCAD zum Öffnen hat, hat die Umwandlung schon auf dem Rechner:
FreeCADCmd läuft ohne Fenster, und `cad_skript.py` erledigt darin einen ganzen Stapel mit einem Start.

Nicht an echtem FreeCAD geprüft sind: der Aufruf über AppImage und der Rückfall `-c`, die Namen der Flatpak-Konsole und
`Part.read` / `MeshPart.meshFromShape` in `cad_skript.py`. Die Suite prüft das Protokoll mit einer Attrappe.
"""
import json
import logging
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time

log = logging.getLogger("partatlas.cad")

SKRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cad_skript.py")
STAPEL = 25                      # Dateien je FreeCAD-Start: ein Start kostet Sekunden, ein sehr langer Stapel hält Ergebnisse zurück
START_ZEIT = 120.0               # bis FreeCAD die erste Datei anfasst (Start, Module laden)
ZEIT_JE_DATEI = 180.0            # eine Datei, die länger braucht, gilt als hängend: sie wird übersprungen
ABWEICHUNG_MM = 0.1              # Vernetzung: für Vorschau, Masse und Gewicht genau genug
WINKEL_RAD = 0.5
FLATPAK_KENNUNG = "org.freecad.FreeCAD"
KONSOLE = ("freecadcmd", "FreeCADCmd", "FreeCADCmd.exe")


def konsole_befehl(programm):
    """Der Aufruf von FreeCAD ohne Fenster, aus dem Pfad des erkannten Programms. None, wenn es kein FreeCAD ist."""
    if not programm:
        return None
    name = os.path.basename(programm)
    if "freecad" not in name.lower():
        return None
    if name == FLATPAK_KENNUNG:
        return ["flatpak", "run", "--command=FreeCADCmd", FLATPAK_KENNUNG] if shutil.which("flatpak") else None
    for ordner in dict.fromkeys([os.path.dirname(programm), os.path.dirname(os.path.realpath(programm))]):
        for n in KONSOLE:
            p = os.path.join(ordner, n)
            if os.path.isfile(p):
                return [p]
    gefunden = next((shutil.which(n) for n in KONSOLE if shutil.which(n)), None)
    if gefunden:
        return [gefunden]
    # AppImage und Programme ohne eigene Konsole: dieselbe Datei im Konsolenmodus.
    return [programm, "-c"]


def _beenden(proc):
    if proc.poll() is not None:
        return
    try:
        if hasattr(os, "killpg"):
            os.killpg(proc.pid, signal.SIGKILL)       # eigene Sitzung: auch Kindprozesse von FreeCAD
        else:
            proc.kill()
    except (OSError, ProcessLookupError):
        pass
    try:
        proc.wait(5)
    except subprocess.TimeoutExpired:
        pass


def _stapel(befehl, stueck, stopp, ordner):
    """Ein FreeCAD-Start für `stueck` [(Schlüssel, Quelle, Ziel)]. Liefert (Schlüssel, ok, Dreiecke | Meldung), sobald
    FreeCAD sie geschrieben hat. Endet, wenn alle da sind, FreeCAD sich beendet, eine Datei hängt oder `stopp` gesetzt wird."""
    os.makedirs(ordner, exist_ok=True)
    arbeit = tempfile.mkdtemp(prefix="stapel_", dir=ordner)
    ergebnis, protokoll, jobpfad = (os.path.join(arbeit, n) for n in ("ergebnis.jsonl", "ausgabe.log", "job.json"))
    with open(jobpfad, "w", encoding="utf-8") as f:
        json.dump({"auftraege": [{"quelle": q, "ziel": z} for _, q, z in stueck], "abweichung": ABWEICHUNG_MM,
                   "winkel": WINKEL_RAD, "ergebnis": ergebnis}, f)
    open(ergebnis, "w").close()
    optionen = {"stdin": subprocess.DEVNULL, "start_new_session": True} if not sys.platform.startswith("win") \
        else {"stdin": subprocess.DEVNULL, "creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | 0x00004000}    # + BELOW_NORMAL_PRIORITY_CLASS
    # Niedrige Priorität, damit die Oberfläche bedienbar bleibt, solange FreeCAD rechnet (`nice` ersetzt sich selbst durch den Aufruf).
    # Nur wenn das Programm da ist: sonst meldete `nice` den Fehler, und die Meldung „liess sich nicht starten“ ginge verloren.
    if not sys.platform.startswith("win") and shutil.which("nice") and shutil.which(befehl[0]):
        befehl = ["nice", "-n", "10", *befehl]
    try:
        with open(protokoll, "wb") as aus:
            proc = subprocess.Popen([*befehl, SKRIPT], env={**os.environ, "PARTATLAS_CAD_JOB": jobpfad},
                                    stdout=aus, stderr=subprocess.STDOUT, **optionen)
    except OSError as e:
        for k, _, _ in stueck:
            yield k, False, f"FreeCAD liess sich nicht starten: {e}"
        shutil.rmtree(arbeit, ignore_errors=True)
        return
    fertig, laeuft_seit, gelesen, aktuell = set(), time.monotonic(), 0, None
    log.info("FreeCAD gestartet (Prozess %s) für einen Stapel von %d Dateien", proc.pid, len(stueck))
    try:
        while True:
            if stopp.is_set():
                return
            with open(ergebnis, encoding="utf-8") as f:
                zeilen = f.read().splitlines()
            neu = zeilen[gelesen:]
            if neu:
                gelesen, laeuft_seit = len(zeilen), time.monotonic()
            for z in neu:
                try:
                    z = json.loads(z)
                except ValueError:
                    continue                      # halb geschriebene Zeile: beim nächsten Mal vollständig
                i = z["i"]
                if z.get("start"):
                    aktuell = i
                    # Bleibt FreeCAD hängen, steht hier die Datei, an der es hing.
                    log.info("FreeCAD beginnt mit Datei %d von %d: %s", i + 1, len(stueck), os.path.basename(stueck[i][1]))
                elif z.get("ok") or z.get("fehler"):
                    fertig.add(i)
                    aktuell = None
                    yield stueck[i][0], bool(z.get("ok")), z.get("dreiecke") if z.get("ok") else z.get("fehler")
                    laeuft_seit = time.monotonic()     # die Zeit, die der Aufrufer mit dem Ergebnis verbrachte, zählt nicht
            if len(fertig) == len(stueck):
                try:
                    proc.wait(5)                  # FreeCADCmd beendet sich nach dem Skript; sonst nachhelfen
                except subprocess.TimeoutExpired:
                    pass
                return
            if proc.poll() is not None and not neu:
                # FreeCAD ist weg, ohne alles geschafft zu haben: die Datei, an der es hing, ist die Ursache.
                if aktuell is not None:
                    fertig.add(aktuell)
                    yield stueck[aktuell][0], False, "FreeCAD wurde beendet (vermutlich zu wenig Speicher für diese Datei)"
                elif not fertig and gelesen == 0:
                    for i, (k, _, _) in enumerate(stueck):
                        yield k, False, "FreeCAD hat nicht gearbeitet: " + _ende(protokoll)
                return
            grenze = ZEIT_JE_DATEI if aktuell is not None else START_ZEIT if gelesen == 0 else ZEIT_JE_DATEI
            if time.monotonic() - laeuft_seit > grenze:
                _beenden(proc)
                log.warning("FreeCAD: Zeitgrenze überschritten (%s), Prozess %s beendet", os.path.basename(stueck[aktuell][1]) if aktuell is not None else "vor der ersten Datei", proc.pid)
                if aktuell is not None:
                    fertig.add(aktuell)
                    yield stueck[aktuell][0], False, f"Zeitgrenze von {int(ZEIT_JE_DATEI)} s überschritten"
                else:
                    for k, _, _ in stueck:
                        yield k, False, "FreeCAD hat nicht rechtzeitig gestartet: " + _ende(protokoll)
                return
            time.sleep(0.15)
    finally:
        _beenden(proc)
        shutil.rmtree(arbeit, ignore_errors=True)


def _ende(protokoll, zeichen=300):
    try:
        with open(protokoll, "rb") as f:
            return f.read()[-zeichen:].decode("utf-8", "replace").strip() or "keine Ausgabe"
    except OSError:
        return "keine Ausgabe"


def umwandeln(befehl, aufgaben, stopp, ordner):
    """Wandelt `aufgaben` [(Schlüssel, Quelle, Ziel)] in Stapeln um und liefert (Schlüssel, ok, Dreiecke | Meldung) nach
    und nach. Eine hängende Datei wird als Fehler gemeldet, FreeCAD für den Rest neu gestartet. `stopp` beendet sofort."""
    offen = list(aufgaben)
    while offen and not stopp.is_set():
        stueck, erledigt = offen[:STAPEL], set()
        for k, ok, info in _stapel(befehl, stueck, stopp, ordner):
            erledigt.add(k)
            yield k, ok, info
        offen = [a for a in offen if a[0] not in erledigt]
        if not erledigt and not stopp.is_set():
            break                                  # kein Fortschritt: nicht endlos neu starten
