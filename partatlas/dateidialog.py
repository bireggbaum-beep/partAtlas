"""
Der Dateidialog des Betriebssystems — „Programm auswählen …“ in den Einstellungen.

Der Browser kann keinen Pfad liefern (er sieht aus Sicherheitsgründen nur den
Dateinamen), und eine Pfadeingabe von Hand ist keine Bedienung. Server und
Anwender sitzen am selben Rechner (KONZEPT §2): der Server öffnet den Dialog,
den der Rechner ohnehin hat, und gibt den gewählten Pfad zurück.

Windows: Windows-Formulare über PowerShell. macOS: AppleScript. Linux: zenity
(GNOME), kdialog (KDE) oder, wenn beides fehlt, Tk aus der Python-Installation.
"""
import importlib.util
import os
import shutil
import subprocess
import sys


class KeinDialog(Exception):
    """Auf diesem Rechner lässt sich kein Dateidialog öffnen."""


def _lauf(befehl):
    """Antwort des Dialogs; None, wenn abgebrochen. Der Anwender darf sich Zeit lassen."""
    r = subprocess.run(befehl, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=900)
    pfad = r.stdout.strip()
    if r.returncode != 0 or not pfad:
        return None
    return pfad


def programm_waehlen(titel):
    """Pfad des gewählten Programms, None bei „Abbrechen“; KeinDialog, wenn es keinen Dialog gibt."""
    return _waehlen(titel, ordner=False)


def ordner_waehlen(titel):
    """Pfad des gewählten Ordners, None bei „Abbrechen“; KeinDialog, wenn es keinen Dialog gibt."""
    return _waehlen(titel, ordner=True)


def _waehlen(titel, ordner):
    if sys.platform.startswith("win"):
        if ordner:
            skript = ("Add-Type -AssemblyName System.Windows.Forms; $d = New-Object System.Windows.Forms.FolderBrowserDialog; "
                      f"$d.Description = '{titel}'; $d.ShowNewFolderButton = $true; "
                      "if ($d.ShowDialog() -eq 'OK') { [Console]::Out.Write($d.SelectedPath) }")
        else:
            skript = ("Add-Type -AssemblyName System.Windows.Forms; $d = New-Object System.Windows.Forms.OpenFileDialog; "
                      f"$d.Title = '{titel}'; $d.Filter = 'Programme (*.exe)|*.exe|Alle Dateien|*.*'; "
                      "$d.InitialDirectory = $env:ProgramFiles; "
                      "if ($d.ShowDialog() -eq 'OK') { [Console]::Out.Write($d.FileName) }")
        return _lauf(["powershell", "-NoProfile", "-STA", "-Command", skript])
    if sys.platform == "darwin":
        ort = "path to home folder" if ordner else "path to applications folder"
        art = "folder" if ordner else "file"
        pfad = _lauf(["osascript", "-e", f'POSIX path of (choose {art} with prompt "{titel}" default location ({ort}))'])
        return pfad.rstrip("/") if pfad else None
    start = os.path.expanduser("~") + "/" if ordner else "/usr/bin/"
    if shutil.which("zenity"):
        return _lauf(["zenity", "--file-selection", *(["--directory"] if ordner else []), f"--title={titel}", f"--filename={start}"])
    if shutil.which("kdialog"):
        return _lauf(["kdialog", "--title", titel, "--getexistingdirectory" if ordner else "--getopenfilename", start])
    if (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")) and importlib.util.find_spec("tkinter"):
        frage = "askdirectory" if ordner else "askopenfilename"
        tk = ("import tkinter, tkinter.filedialog as f; r = tkinter.Tk(); r.withdraw(); "
              f"print(f.{frage}(title={titel!r}, initialdir={start!r}))")
        return _lauf([sys.executable, "-c", tk])
    raise KeinDialog("Auf diesem Rechner lässt sich kein Dateidialog öffnen. Installiere zenity oder kdialog (Manjaro/Arch: sudo pacman -S zenity).")
