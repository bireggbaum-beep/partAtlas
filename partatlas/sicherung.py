"""
Sicherungen der Datenbank — damit kein Fehler (im Programm oder beim Bedienen) Katalogdaten endgültig kostet.

Was gesichert wird: `datenbank/` (flatgraph: Modelle, Tags, Drucke, Baugruppen, Sammlungen, Ordner), `vault_text/` (lange Texte)
und `einstellungen.json`. Nicht der Vault mit Bildern: er wächst nur (KONZEPT §3.2), seine Dateien bleiben gültig.

Wann: beim Start (höchstens alle 10 Minuten) und vor jeder Massenaktion immer (Wurzelordner entfernen, Ordner aus dem Katalog
entfernen, mehrere Modelle entfernen). Kopiert wird unter der Sperre von flatgraph (eine leere Transaktion hält sie): kein anderer
Thread schreibt währenddessen, die Kopie ist ein Stand und keine Mischung. Fertig ist eine Sicherung erst nach `os.replace` des
Arbeitsordners — eine abgebrochene liegt als `.…arbeit` da und zählt nicht.

Behalten: die neuesten 20 und dazu die erste jedes Tages für 60 Tage. Zurückholen nur bei beendetem partAtlas:
    python -m partatlas.sicherung                 Sicherungen auflisten
    python -m partatlas.sicherung --jetzt         eine anlegen
    python -m partatlas.sicherung --zurueck NAME  diesen Stand zurückholen (der jetzige wird vorher selbst gesichert)
"""
import os
import re
import shutil
import sys
import time

ORDNER = "sicherungen"
TEILE = ("datenbank", "vault_text", "einstellungen.json")
MINDESTABSTAND_S = 600
NEUESTE = 20
TAGE = 60
# Zeit, dann ein immer zweistelliger Zähler: so ist die Reihenfolge der Namen die der Entstehung, auch in derselben Sekunde.
_NAME = re.compile(r"^(\d{4}-\d{2}-\d{2})_(\d{6})-(\d{2})__([\w-]+)$")


def _ordner(wurzel):
    return os.path.join(wurzel, ORDNER)


def liste(wurzel):
    """[{name, zeit, grund, bytes}] der fertigen Sicherungen, neueste zuerst."""
    basis = _ordner(wurzel)
    if not os.path.isdir(basis):
        return []
    aus = []
    for n in os.listdir(basis):
        m = _NAME.match(n)
        if not m or not os.path.isdir(os.path.join(basis, n)):
            continue
        groesse = sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(os.path.join(basis, n)) for f in fs)
        aus.append({"name": n, "zeit": f"{m.group(1)} {m.group(2)[:2]}:{m.group(2)[2:4]}:{m.group(2)[4:]}", "grund": m.group(4),
                    "bytes": groesse})
    return sorted(aus, key=lambda x: x["name"], reverse=True)


def _kopieren(wurzel, ziel):
    os.makedirs(ziel)
    for teil in TEILE:
        quelle = os.path.join(wurzel, teil)
        if os.path.isdir(quelle):
            shutil.copytree(quelle, os.path.join(ziel, teil))
        elif os.path.isfile(quelle):
            shutil.copy2(quelle, os.path.join(ziel, teil))


def sichern(bestand, grund, immer=False):
    """Legt eine Sicherung an; gibt ihren Namen zurück oder None, wenn die letzte jünger als 10 Minuten ist und `immer` fehlt."""
    basis = _ordner(bestand.wurzel)
    os.makedirs(basis, exist_ok=True)
    vorhanden = liste(bestand.wurzel)
    if not immer and vorhanden:
        letzte = time.mktime(time.strptime(vorhanden[0]["zeit"], "%Y-%m-%d %H:%M:%S"))
        if time.time() - letzte < MINDESTABSTAND_S:
            return None
    grund = re.sub(r"[^\w-]+", "-", grund).strip("-") or "sicherung"
    stamm = time.strftime("%Y-%m-%d_%H%M%S")
    # Hinter der höchsten Nummer dieser Sekunde, nie in einer Lücke: eine frei geräumte niedrige Nummer sortierte die neue Sicherung
    # als älteste, und das Aufräumen gleich danach nähme sie wieder weg.
    belegt = [x.lstrip(".")[len(stamm) + 1:len(stamm) + 3] for x in os.listdir(basis) if x.lstrip(".").startswith(stamm + "-")]
    n = 1 + max((int(x) for x in belegt if x.isdigit()), default=0)
    name = f"{stamm}-{n:02d}__{grund}"
    arbeit = os.path.join(basis, f".{name}.arbeit")
    with bestand.db.transaction():       # hält die Sperre: kein Schreiben anderer Threads während des Kopierens
        _kopieren(bestand.wurzel, arbeit)
    os.replace(arbeit, os.path.join(basis, name))
    _aufraeumen(bestand.wurzel)
    return name


def _aufraeumen(wurzel):
    """Alte Sicherungen gehen, aber nie die neuesten 20 und nie die erste eines Tages der letzten 60 Tage."""
    alle = liste(wurzel)
    behalten = {s["name"] for s in alle[:NEUESTE]}
    grenze = time.strftime("%Y-%m-%d", time.localtime(time.time() - TAGE * 86400))
    erste_des_tages = {}
    for s in reversed(alle):                 # älteste zuerst: die erste je Tag gewinnt
        erste_des_tages.setdefault(s["zeit"][:10], s["name"])
    behalten |= {n for tag, n in erste_des_tages.items() if tag >= grenze}
    basis = os.path.realpath(_ordner(wurzel))
    for s in alle:
        if s["name"] not in behalten:
            pfad = os.path.realpath(os.path.join(basis, s["name"]))
            if os.path.dirname(pfad) == basis:       # nur Sicherungen, nie etwas anderes
                shutil.rmtree(pfad)


def zurueckholen(wurzel, name):
    """Ersetzt die Datenbank durch eine Sicherung. Nur bei beendetem partAtlas: flatgraph lässt keinen zweiten Besitzer zu, und
    das Öffnen hier beweist, dass keiner da ist. Der jetzige Stand wird vorher gesichert und bleibt zusätzlich in `arbeit/` liegen:
    auch das Zurückholen ist umkehrbar."""
    from .bestand import Bestand
    quelle = os.path.join(_ordner(wurzel), name)
    if not _NAME.match(name) or not os.path.isdir(quelle):
        raise ValueError(f"Keine Sicherung: {name}")
    b = Bestand(wurzel)                       # wirft BestandBelegt, solange partAtlas läuft
    try:
        sichern(b, "vor-zurueckholen", immer=True)
    finally:
        b.schliessen()
    beiseite = os.path.join(wurzel, "arbeit", f"datenbank_ersetzt_{time.strftime('%Y-%m-%d_%H%M%S')}")
    os.makedirs(os.path.dirname(beiseite), exist_ok=True)
    os.replace(os.path.join(wurzel, "datenbank"), beiseite)
    shutil.copytree(os.path.join(quelle, "datenbank"), os.path.join(wurzel, "datenbank"))
    # Lange Texte: nur ergänzen, was fehlt — eine neuere Datei bleibt, die alte Datenbank verweist auf ihre eigenen.
    texte = os.path.join(quelle, "vault_text")
    for ordner, _, dateien in os.walk(texte):
        for d in dateien:
            ziel = os.path.join(wurzel, "vault_text", os.path.relpath(os.path.join(ordner, d), texte))
            if not os.path.exists(ziel):
                os.makedirs(os.path.dirname(ziel), exist_ok=True)
                shutil.copy2(os.path.join(ordner, d), ziel)
    return beiseite


def _haupt(argv):
    from .bestand import standard_ort
    wurzel = os.path.abspath(os.environ.get("PARTATLAS_BESTAND") or standard_ort())
    if "--zurueck" in argv:
        name = argv[argv.index("--zurueck") + 1]
        beiseite = zurueckholen(wurzel, name)
        print(f"Zurückgeholt: {name}. Der vorige Stand liegt in {beiseite} und als Sicherung „vor-zurueckholen“.")
        return
    if "--jetzt" in argv:
        from .bestand import Bestand
        b = Bestand(wurzel)
        try:
            print("Angelegt:", sichern(b, "von-hand", immer=True))
        finally:
            b.schliessen()
        return
    print(f"Sicherungen in {_ordner(wurzel)}:")
    for s in liste(wurzel):
        print(f"  {s['name']}   {s['bytes'] / 1e6:.1f} MB")


if __name__ == "__main__":
    _haupt(sys.argv[1:])
