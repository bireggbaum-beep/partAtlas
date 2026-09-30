"""
„Im Slicer öffnen“ — wie im 3MF Katalog (`src-tauri/src/slicers.rs`):
bekannte Installationsorte absuchen, eigene Einträge erlauben, die Datei
übergeben. Server und Slicer laufen auf demselben Rechner (KONZEPT §2).

Gestartet wird nur, was hier gefunden oder vom Anwender eingetragen wurde,
und nur mit einer Datei, die der Katalog kennt — nie ein Pfad aus der
Anfrage.
"""
import glob
import os
import shutil
import subprocess
import sys

BEKANNT = [
    ("Bambu Studio", ["bambu-studio", "BambuStudio", "bambustudio", "com.bambulab.BambuStudio"],
     ["*Bambu*Studio*.AppImage"]),
    ("OrcaSlicer", ["orca-slicer", "OrcaSlicer", "io.github.softfever.OrcaSlicer", "com.orcaslicer.OrcaSlicer"],
     ["*Orca*Slicer*.AppImage", "*OrcaSlicer*.AppImage"]),
    ("PrusaSlicer", ["prusa-slicer", "prusaslicer", "com.prusa3d.PrusaSlicer"], ["*PrusaSlicer*.AppImage"]),
    ("SuperSlicer", ["superslicer"], ["*SuperSlicer*.AppImage"]),
    ("UltiMaker Cura", ["cura", "UltiMaker-Cura", "com.ultimaker.cura"], ["*UltiMaker-Cura*.AppImage"]),
]

WINDOWS = {
    "Bambu Studio": [r"Bambu Studio\bambu-studio.exe"],
    "OrcaSlicer": [r"OrcaSlicer\orca-slicer.exe"],
    "PrusaSlicer": [r"Prusa3D\PrusaSlicer\prusa-slicer.exe"],
    "SuperSlicer": [r"SuperSlicer\superslicer.exe"],
}


def _linux_ordner():
    home = os.path.expanduser("~")
    return ["/usr/bin", "/usr/local/bin", "/var/lib/flatpak/exports/bin",
            os.path.join(home, ".local/share/flatpak/exports/bin"), os.path.join(home, ".local/bin"),
            os.path.join(home, "Applications"), os.path.join(home, "AppImages"),
            os.path.join(home, "Downloads")]


def erkennen():
    gefunden = []
    if sys.platform.startswith("win"):
        basen = [os.environ.get(v) for v in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA")]
        for name, teile in WINDOWS.items():
            for b in filter(None, basen):
                for t in teile:
                    p = os.path.join(b, t)
                    if os.path.isfile(p):
                        gefunden.append({"name": name, "pfad": p})
    else:
        for name, programme, appimages in BEKANNT:
            for prog in programme:
                p = shutil.which(prog)
                if p:
                    gefunden.append({"name": name, "pfad": p})
            for ordner in _linux_ordner():
                for prog in programme:
                    p = os.path.join(ordner, prog)
                    if os.path.isfile(p) and os.access(p, os.X_OK):
                        gefunden.append({"name": name, "pfad": p})
                for muster in appimages:
                    for p in glob.glob(os.path.join(ordner, muster)):
                        gefunden.append({"name": name, "pfad": p})
            for prog in programme:
                for p in glob.glob(f"/opt/{prog}*/{prog}"):
                    gefunden.append({"name": name, "pfad": p})
    ergebnis, gesehen = [], set()
    for s in gefunden:
        echt = os.path.realpath(s["pfad"])
        if echt not in gesehen:
            gesehen.add(echt)
            ergebnis.append(s)
    return ergebnis


def alle(einstellungen):
    eigene = [{"name": s["name"], "pfad": s["pfad"], "eigen": True}
              for s in einstellungen.get("slicer", []) if os.path.isfile(s.get("pfad", ""))]
    pfade = {os.path.realpath(s["pfad"]) for s in eigene}
    return eigene + [s for s in erkennen() if os.path.realpath(s["pfad"]) not in pfade]


def oeffnen(programm, datei):
    # Eigene Sitzung und keine Ausgabe: der Slicer lebt weiter, wenn der
    # Server endet, und schreibt nicht in unser Protokoll.
    optionen = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if sys.platform.startswith("win"):
        optionen["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        optionen["start_new_session"] = True
    subprocess.Popen([programm, datei], **optionen)
