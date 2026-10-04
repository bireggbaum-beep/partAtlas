"""
„Öffnen in …“ — Slicer wie im 3MF Katalog (`src-tauri/src/slicers.rs`),
dazu CAD (FreeCAD). Bekannte Installationsorte absuchen, eigene Einträge
erlauben, je Format ein Standardprogramm, die Datei übergeben. Server und
Programme laufen auf demselben Rechner (KONZEPT §2).

Gestartet wird nur, was hier gefunden oder vom Anwender eingetragen wurde,
und nur mit einer Datei, die der Katalog kennt — nie ein Pfad aus der
Anfrage.
"""
import glob
import os
import shutil
import subprocess
import sys
import time
import urllib.parse

SLICER, CAD = "slicer", "cad"
ARTEN = {SLICER: "Slicer", CAD: "CAD / Modeller"}
FORMATE = ("3mf", "stl", "obj", "step", "fcstd")
CAD_FORMATE = ("step", "fcstd")        # gehören ins CAD, ein Slicer kennt sie nicht

# name, art, Formate, Programmnamen (PATH, flatpak-Export), AppImage-Muster,
# Windows-Muster relativ zu ProgramFiles bzw. LOCALAPPDATA\Programs.
# Die Formate sind, was das Programm beim Start mit Datei öffnet: Cura
# liest STEP nur mit Zusatz. FreeCAD öffnet 3MF als Netz (ohne Slicer-Daten wie Platten und Farben); als Standard
# bleibt für 3MF der Slicer, FreeCAD ist nur im Menü „Öffnen mit“.
BEKANNT = [
    ("Bambu Studio", SLICER, ("3mf", "stl", "obj", "step"),
     ["bambu-studio", "BambuStudio", "bambustudio", "com.bambulab.BambuStudio"],
     ["*Bambu*Studio*.AppImage"], [r"Bambu Studio\bambu-studio.exe"]),
    ("OrcaSlicer", SLICER, ("3mf", "stl", "obj", "step"),
     ["orca-slicer", "OrcaSlicer", "io.github.softfever.OrcaSlicer", "com.orcaslicer.OrcaSlicer"],
     ["*Orca*Slicer*.AppImage", "*OrcaSlicer*.AppImage"], [r"OrcaSlicer\orca-slicer.exe"]),
    ("PrusaSlicer", SLICER, ("3mf", "stl", "obj", "step"),
     ["prusa-slicer", "prusaslicer", "com.prusa3d.PrusaSlicer"],
     ["*PrusaSlicer*.AppImage"], [r"Prusa3D\PrusaSlicer\prusa-slicer.exe"]),
    ("SuperSlicer", SLICER, ("3mf", "stl", "obj"),
     ["superslicer"], ["*SuperSlicer*.AppImage"], [r"SuperSlicer\superslicer.exe"]),
    ("UltiMaker Cura", SLICER, ("3mf", "stl", "obj"),
     ["cura", "UltiMaker-Cura", "com.ultimaker.cura"], ["*UltiMaker-Cura*.AppImage"],
     [r"UltiMaker Cura*\UltiMaker-Cura.exe"]),
    # Anycubic Slicer Next baut auf OrcaSlicer auf. Programmnamen und Orte
    # sind nicht an einer Installation geprüft, deshalb breit gefasst;
    # wer nicht gefunden wird, trägt sich in den Einstellungen ein.
    ("Anycubic Slicer", SLICER, ("3mf", "stl", "obj", "step"),
     ["AnycubicSlicerNext", "anycubicslicernext", "anycubic-slicer-next", "AnycubicSlicer", "anycubicslicer"],
     ["*Anycubic*Slicer*.AppImage", "*Anycubic*Slicer*.appimage"],
     [r"AnycubicSlicer*\AnycubicSlicer*.exe", r"Anycubic*\AnycubicSlicer*.exe"]),
    ("FreeCAD", CAD, ("step", "stl", "obj", "fcstd", "3mf"),
     ["freecad", "FreeCAD", "org.freecad.FreeCAD", "freecad-daily"],
     ["*FreeCAD*.AppImage"], [r"FreeCAD*\bin\freecad.exe"]),
]


def _linux_ordner():
    home = os.path.expanduser("~")
    return ["/usr/bin", "/usr/local/bin", "/opt", "/var/lib/flatpak/exports/bin",
            os.path.join(home, ".local/share/flatpak/exports/bin"), os.path.join(home, ".local/bin"), os.path.join(home, "bin"),
            os.path.join(home, "Applications"), os.path.join(home, "AppImages"), os.path.join(home, "Apps"),
            os.path.join(home, "Downloads"), os.path.join(home, "Desktop"), os.path.join(home, "Schreibtisch")]


# Flatpak legt die Programme unter ihrer Kennung ab („org.freecad.FreeCAD“); bei Programmen, deren Kennung wir nicht
# kennen (Anycubic Slicer: Flatpak von Dritten), genügt das Stichwort im Namen.
STICHWORT = {"Bambu Studio": "bambustudio", "OrcaSlicer": "orcaslicer", "PrusaSlicer": "prusaslicer", "SuperSlicer": "superslicer",
             "UltiMaker Cura": ".cura", "Anycubic Slicer": "anycubic", "FreeCAD": "freecad"}
FLATPAK_ORDNER = ("/var/lib/flatpak/exports/bin", os.path.join("~", ".local/share/flatpak/exports/bin"))


def _eintrag(name, art, formate, pfad):
    return {"name": name, "art": art, "formate": list(formate), "pfad": pfad}


def erkennen():
    gefunden = []
    if sys.platform.startswith("win"):
        basen = [os.environ.get(v) for v in ("ProgramFiles", "ProgramFiles(x86)")]
        if os.environ.get("LOCALAPPDATA"):
            basen.append(os.path.join(os.environ["LOCALAPPDATA"], "Programs"))
        for name, art, formate, _, _, muster in BEKANNT:
            for b in filter(None, basen):
                for m in muster:
                    for p in sorted(glob.glob(os.path.join(b, m)), reverse=True):
                        if os.path.isfile(p):
                            gefunden.append(_eintrag(name, art, formate, p))
    else:
        # PATH zuerst: damit gewinnt, was der Anwender selbst vorne hat.
        for name, art, formate, programme, appimages, _ in BEKANNT:
            for prog in programme:
                p = shutil.which(prog)
                if p:
                    gefunden.append(_eintrag(name, art, formate, p))
            for ordner in _linux_ordner():
                for prog in programme:
                    p = os.path.join(ordner, prog)
                    if os.path.isfile(p) and os.access(p, os.X_OK):
                        gefunden.append(_eintrag(name, art, formate, p))
                for muster in appimages:
                    for p in glob.glob(os.path.join(ordner, muster)):
                        # Ohne Ausführrecht startet eine AppImage nicht: erst gar nicht anbieten, der Anwender wählt sie dann
                        # selbst und bekommt gesagt, woran es liegt.
                        if os.access(p, os.X_OK):
                            gefunden.append(_eintrag(name, art, formate, p))
            wort = STICHWORT.get(name)
            for ordner in FLATPAK_ORDNER:
                ordner = os.path.expanduser(ordner)
                if wort and os.path.isdir(ordner):
                    for datei in sorted(os.listdir(ordner)):
                        p = os.path.join(ordner, datei)
                        if wort in datei.lower() and os.path.isfile(p) and os.access(p, os.X_OK):
                            gefunden.append(_eintrag(name, art, formate, p))
            for prog in programme:
                for p in glob.glob(f"/opt/{prog}*/{prog}"):
                    gefunden.append(_eintrag(name, art, formate, p))
    ergebnis, gesehen = [], set()
    for s in gefunden:
        echt = os.path.realpath(s["pfad"])
        if echt not in gesehen:
            gesehen.add(echt)
            ergebnis.append(s)
    return ergebnis


def eigene(einstellungen):
    # Einträge aus früheren Fassungen („slicer“ seit 0.6, „programme“): sie bleiben gültig,
    # bis der Anwender in den Einstellungen selbst ein Programm wählt.
    roh = [{**s, "art": SLICER} for s in einstellungen.get("slicer", [])] + einstellungen.get("programme", [])
    return [{**_eintrag(s["name"], s.get("art") if s.get("art") in ARTEN else CAD, s.get("formate") or FORMATE,
                        s["pfad"]), "eigen": True}
            for s in roh if s.get("pfad") and os.path.isfile(s["pfad"])]


def eintrag_fuer(pfad, art):
    """Ein vom Anwender gewähltes Programm. Der Name kommt vom bekannten Programm,
    sonst vom Dateinamen („prusa-slicer.AppImage“ → „prusa-slicer“)."""
    echt = os.path.basename(os.path.realpath(pfad)).lower()
    for name, _, _, programme, _, _ in BEKANNT:
        if echt.rsplit(".", 1)[0] in {x.lower() for x in programme}:
            return {**_eintrag(name, art, FORMATE, pfad), "eigen": True}
    stamm = os.path.basename(pfad.rstrip("/\\"))
    for ende in (".AppImage", ".appimage", ".exe", ".app"):
        if stamm.endswith(ende):
            stamm = stamm[: -len(ende)]
    return {**_eintrag(stamm, art, FORMATE, pfad), "eigen": True}


def programm_fuer(art, einstellungen, erkannt=None):
    """Das Programm für „Slicer“ bzw. „CAD“: was der Anwender gewählt hat, sonst ein
    Eintrag aus früheren Fassungen, sonst das erste gefundene. None, wenn es keines gibt."""
    gewaehlt = (einstellungen.get("programm") or {}).get(art)
    if gewaehlt and ausfuehrbar(gewaehlt):
        return eintrag_fuer(gewaehlt, art)
    alt = next((s for s in eigene(einstellungen) if s["art"] == art), None)
    if alt:
        return alt
    return next((s for s in (erkannt if erkannt is not None else erkennen()) if s["art"] == art), None)


def alle(einstellungen):
    """Genau zwei Plätze: ein Slicer und ein CAD."""
    gefunden = erkennen()
    return [p for p in (programm_fuer(art, einstellungen, gefunden) for art in (SLICER, CAD)) if p]


def standard(programme, einstellungen=None):
    """Je Format das Programm, das der Hauptknopf nimmt: STEP und FCStd ins CAD (ein Slicer
    würde STEP nur vernetzen und FCStd gar nicht kennen), alles andere in den Slicer — so wie man druckt."""
    ergebnis = {}
    for fmt in FORMATE:
        passend = [p for p in programme if fmt in p["formate"]]
        vorzug = CAD if fmt in CAD_FORMATE else SLICER
        wahl = next((p for p in passend if p["art"] == vorzug), None) or (passend[0] if passend else None)
        ergebnis[fmt] = wahl["pfad"] if wahl else None
    return ergebnis


def ausfuehrbar(pfad):
    if sys.platform == "darwin" and pfad.endswith(".app") and os.path.isdir(pfad):
        return True         # ein Programm ist am Mac ein Ordner
    return os.path.isfile(pfad) and (sys.platform.startswith("win") or os.access(pfad, os.X_OK))


def _optionen():
    # Eigene Sitzung und keine Ausgabe: das Programm lebt weiter, wenn der
    # Server endet, und schreibt nicht in unser Protokoll.
    optionen = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if sys.platform.startswith("win"):
        optionen["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        optionen["start_new_session"] = True
    return optionen


def oeffnen(programm, datei, protokoll=None):
    """Startet das Programm mit der Datei. Seine Ausgabe geht in `protokoll` (wenn gegeben): sonst weiss niemand,
    warum ein Start nicht klappte. Beendet es sich innerhalb von 1,2 s mit Fehler, wird das gemeldet — samt dem
    Anfang seiner Ausgabe; ein Programm, das weiterläuft, hat gestartet."""
    befehl = ["open", "-a", programm, datei] if programm.endswith(".app") else [programm, datei]
    optionen = _optionen()
    start = 0
    log = None
    if protokoll:
        os.makedirs(os.path.dirname(protokoll), exist_ok=True)
        log = open(protokoll, "ab")
        log.write(f"\n--- {time.strftime('%d.%m.%Y %H:%M:%S')}  {' '.join(befehl)}\n".encode())
        log.flush()
        start = log.tell()
        optionen["stdout"], optionen["stderr"] = log, subprocess.STDOUT
    try:
        prozess = subprocess.Popen(befehl, **optionen)
    finally:
        if log:
            log.close()
    try:
        code = prozess.wait(timeout=1.2)
    except subprocess.TimeoutExpired:
        return
    if code == 0:
        return          # etwa ein Starter, der an ein laufendes Programm übergibt
    ausgabe = ""
    if protokoll and os.path.exists(protokoll):
        with open(protokoll, "rb") as f:
            f.seek(start)
            ausgabe = f.read(600).decode("utf-8", "replace").strip()
    hinweis = (" AppImages brauchen FUSE — auf Manjaro/Arch: sudo pacman -S fuse2." if programm.lower().endswith(".appimage") else "")
    raise OSError(f"{os.path.basename(programm)} beendete sich sofort (Code {code}).{hinweis}"
                  + (f" Ausgabe: {ausgabe}" if ausgabe else "") + (f" — Protokoll: {protokoll}" if protokoll else ""))


def mit_system(datei):
    """Was der Dateimanager bei Doppelklick täte."""
    if sys.platform.startswith("win"):
        os.startfile(datei)  # noqa: kennt nur Windows
        return
    befehl = "open" if sys.platform == "darwin" else shutil.which("xdg-open")
    if not befehl:
        raise FileNotFoundError("xdg-open fehlt — ohne Desktop kein Standardprogramm.")
    subprocess.Popen([befehl, datei], **_optionen())


def im_ordner_zeigen(datei):
    """Den Dateimanager im Ordner der Datei öffnen, die Datei markiert, wo
    es geht: Windows per explorer /select, Linux über die Freedesktop-
    Schnittstelle (Dolphin, Nautilus, Nemo, Thunar …), sonst nur den Ordner."""
    if sys.platform.startswith("win"):
        subprocess.Popen(["explorer", f"/select,{datei}"], **_optionen())
        return
    if sys.platform == "darwin":
        subprocess.Popen(["open", "-R", datei], **_optionen())
        return
    dbus = shutil.which("dbus-send")
    if dbus:
        uri = "file://" + urllib.parse.quote(os.path.abspath(datei))
        r = subprocess.run([dbus, "--session", "--print-reply", "--dest=org.freedesktop.FileManager1", "--type=method_call",
                            "/org/freedesktop/FileManager1", "org.freedesktop.FileManager1.ShowItems",
                            f"array:string:{uri}", "string:"],
                           stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        if r.returncode == 0:
            return
    mit_system(os.path.dirname(datei))
