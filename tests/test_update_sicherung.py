"""Sicherung vor einem Update: beim ersten Start einer neuen Fassung eine eigene, die das Aufräumen nicht wegnimmt (die letzten drei bleiben)."""
import os
import shutil
import tempfile
import time

import muster
from muster import check
from fastapi.testclient import TestClient
from partatlas import sicherung
from partatlas.bestand import Bestand
from partatlas.main import erstelle_app
from partatlas.version import VERSION


def oeffnen(wurzel):
    with TestClient(erstelle_app(wurzel, prozesse=1)) as c:
        c.get("/api/stand")


def updates(wurzel):
    return [x for x in sicherung.liste(wurzel) if x["grund"] == "vor-update"]


def einstellen(wurzel, **werte):
    """Einstellungen des Bestands setzen; None entfernt den Schlüssel (einstellungen_setzen kann nur hinzufügen)."""
    import json
    from partatlas.dateien import schreibe_atomar
    b = Bestand(wurzel)
    try:
        e = b.einstellungen()
        for k, v in werte.items():
            e.pop(k, None) if v is None else e.__setitem__(k, v)
        schreibe_atomar(b._einstellungen_pfad, json.dumps(e, ensure_ascii=False, indent=1).encode("utf-8"))
    finally:
        b.schliessen()


if __name__ == "__main__":
    tmp = tempfile.mkdtemp()
    w = os.path.join(tmp, "bestand")
    oeffnen(w)
    b = Bestand(w); e = b.einstellungen(); b.schliessen()
    check("Ein neuer Bestand: keine Sicherung vor einem Update, die Fassung ist vermerkt", not updates(w) and e.get("fassung_zuletzt") == VERSION)
    oeffnen(w)
    check("Gleiche Fassung noch einmal: keine", not updates(w))

    einstellen(w, fassung_zuletzt="1.0.0")
    oeffnen(w)
    u = updates(w)
    check("Andere Fassung beim letzten Öffnen: eine Sicherung „vor dem Update“ mit beiden Fassungen",
          len(u) == 1 and u[0]["anlass"] == f"Vor dem Update von 1.0.0 auf {VERSION}")
    b = Bestand(w); fz = b.einstellungen().get("fassung_zuletzt"); b.schliessen()
    check("… danach ist die neue Fassung vermerkt, und der nächste Start legt keine weitere an", fz == VERSION)
    oeffnen(w)
    check("… (nächster Start)", len(updates(w)) == 1)

    # Ein Bestand von 1.0.8: kennt fassung_zuletzt nicht, nur die gesehenen Neuigkeiten
    einstellen(w, fassung_zuletzt=None, neuigkeiten_gesehen="1.0.8")
    oeffnen(w)
    check("Bestand von 1.0.8 (ohne vermerkte Fassung): erkannt an den zuletzt gesehenen Neuigkeiten",
          updates(w)[0]["anlass"] == f"Vor dem Update von 1.0.8 auf {VERSION}")

    # Öffnen scheiterte nach der Sicherung (fassung_zuletzt nicht gesetzt): keine zweite gleiche
    einstellen(w, fassung_zuletzt="1.0.5")
    b = Bestand(w)
    sicherung.beim_start(b, VERSION)
    sicherung.beim_start(b, VERSION)
    b.schliessen()
    check("Scheitert das Öffnen danach, legt der nächste Start keine zweite gleiche an",
          sum(1 for x in updates(w) if x["anlass"] == f"Vor dem Update von 1.0.5 auf {VERSION}") == 1)

    # Aufräumen: alte Sicherungen gehen, die letzten drei „vor dem Update“ bleiben, auch nach 30 Tagen
    basis = os.path.join(w, "sicherungen")
    vorlage = os.path.join(basis, updates(w)[0]["name"])
    alte = []
    for i, tage in enumerate((90, 80, 70, 60)):
        name = time.strftime("%Y-%m-%d", time.localtime(time.time() - tage * 86400)) + f"_1200{i:02d}-01__vor-update"
        shutil.copytree(vorlage, os.path.join(basis, name))
        alte.append(name)
    for x in updates(w):                    # die heutigen weg: nur die alten zählen
        if x["name"] not in alte:
            shutil.rmtree(os.path.join(basis, x["name"]))
    b = Bestand(w)
    for _ in range(7):
        sicherung.sichern(b, "viele", immer=True)
    b.schliessen()
    namen = {x["name"] for x in sicherung.liste(w)}
    check("Aufräumen: die letzten drei Sicherungen vor einem Update bleiben, auch nach 30 Tagen; die ältere geht",
          set(alte[1:]) <= namen and alte[0] not in namen)
    check("… die übrigen Regeln gelten weiter (die neuesten 5)", len([n for n in namen if n.endswith("__viele")]) == 5)
    muster.ende()
