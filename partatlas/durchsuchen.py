"""
Ordner wählen wie im Dateimanager — für „Ordner hinzufügen“, damit niemand
einen Pfad tippen muss. Nur lesen: Namen von Ordnern und wie viele
Modelldateien darin liegen. Server und Anwender sitzen am selben Rechner
(KONZEPT §2); die Wache lässt nur die eigene Seite fragen.
"""
import getpass
import os
import string
import sys

from .formate import FORMATE

# Beim Zählen nicht ewig laufen: ein ganzes Laufwerk hat Millionen Dateien.
# Darüber steht „mehr als …“ — genug, um zu sehen, dass es der richtige Ordner ist.
ZAEHL_GRENZE = 60_000


def _sichtbar(name):
    return not name.startswith(".") and not name.startswith("$")


def zaehlen(pfad):
    """(Modelldateien, vollständig gezählt?)."""
    modelle = gesehen = 0
    for ordner, unter, dateien in os.walk(pfad):
        unter[:] = [u for u in unter if _sichtbar(u)]
        for d in dateien:
            gesehen += 1
            if os.path.splitext(d)[1].lower() in FORMATE:
                modelle += 1
        if gesehen > ZAEHL_GRENZE:
            return modelle, False
    return modelle, True


def sprungziele():
    """Wo man typischerweise anfängt: der eigene Ordner, Downloads und
    Dokumente, eingehängte Laufwerke (USB-Stick, zweite Platte)."""
    home = os.path.expanduser("~")
    ziele = [{"name": "Persönlicher Ordner", "pfad": home, "art": "home"}]
    for name in ("3D-Druck", "3D", "3d-druck", "Downloads", "Dokumente", "Documents", "Schreibtisch", "Desktop"):
        p = os.path.join(home, name)
        if os.path.isdir(p) and not any(z["pfad"] == p for z in ziele):
            ziele.append({"name": name, "pfad": p, "art": "ordner"})
    if sys.platform.startswith("win"):
        for b in string.ascii_uppercase:
            if os.path.isdir(f"{b}:\\"):
                ziele.append({"name": f"Laufwerk {b}:", "pfad": f"{b}:\\", "art": "laufwerk"})
    else:
        benutzer = getpass.getuser()
        for basis in (f"/run/media/{benutzer}", f"/media/{benutzer}", "/mnt"):
            if os.path.isdir(basis):
                for n in sorted(os.listdir(basis)):
                    p = os.path.join(basis, n)
                    if os.path.isdir(p) and _sichtbar(n):
                        ziele.append({"name": n, "pfad": p, "art": "laufwerk"})
    return ziele


def auflisten(pfad=None):
    pfad = os.path.abspath(os.path.expanduser(pfad or "~"))
    if not os.path.isdir(pfad):
        raise FileNotFoundError(pfad)
    try:
        namen = sorted((n for n in os.listdir(pfad) if _sichtbar(n) and os.path.isdir(os.path.join(pfad, n))),
                       key=str.lower)
    except PermissionError:
        namen = []
    eltern = os.path.dirname(pfad)
    modelle, ganz = zaehlen(pfad)
    return {"pfad": pfad, "eltern": eltern if eltern != pfad else None,
            "ordner": [{"name": n, "pfad": os.path.join(pfad, n)} for n in namen],
            "modelle": modelle, "vollstaendig": ganz, "sprungziele": sprungziele()}
