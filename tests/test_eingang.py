"""Die Eingangsliste und der Dienst im Hintergrund: was der Anwender ablegt, wird vorgemerkt und ohne Durchsuchen der Ordner eingelesen;
die Vorschaubilder weichen ihm; ein Abbruch, ein Neustart oder ein verschwundener Browser verliert nichts."""
import json
import os
import tempfile
import time

import muster
from muster import check
from fastapi.testclient import TestClient
from partatlas import scan
from partatlas.bestand import Bestand
from partatlas.eingang import Eingang
from partatlas.katalog import Katalog
from partatlas.main import erstelle_app
from partatlas.scan import Scanner


def namen(k):
    return {m["name"] for m in k.modelle()}


if __name__ == "__main__":
    tmp = tempfile.mkdtemp()
    ordner = os.path.join(tmp, "teile")
    os.makedirs(ordner)
    for i, n in enumerate(("A", "B", "C")):
        muster.stl_binaer(os.path.join(ordner, f"{n}.stl"), 10 + i, 20, 30)
    b = Bestand(os.path.join(tmp, "bestand"))
    k = Katalog(b)
    meldungen = []
    s = Scanner(b, k, melden=lambda st: meldungen.append(dict(st)), prozesse=2)
    w = k.wurzel_hinzufuegen(ordner)
    s.lauf()

    # -- Die Liste selbst
    e = Eingang(b)
    check("Eintragen gibt die Zahl der neuen Einträge zurück, Doppeltes zählt nicht",
          e.eintragen([(w, "x.stl"), (w, "y.stl"), (w, "x.stl")]) == 2 and e.eintragen([(w, "y.stl")]) == 0 and len(e) == 2)
    check("Die Liste steht auf der Platte: eine neue Instanz (Neustart) findet dieselben Einträge in derselben Reihenfolge",
          Eingang(b).liste() == [(w, "x.stl"), (w, "y.stl")])
    e.erledigt([(w, "x.stl")])
    check("Erledigtes wird gestrichen, der Rest bleibt, auch auf der Platte", e.liste() == [(w, "y.stl")] and Eingang(b).liste() == [(w, "y.stl")])
    e.erledigt([(w, "y.stl")])
    check("Eine leere Liste hinterlässt keine Datei", len(e) == 0 and not os.path.exists(b.pfad("arbeit", "eingang.json")))
    with open(b.pfad("arbeit", "eingang.json"), "w") as f:
        f.write("{kaputt")
    check("Eine beschädigte Liste fängt leer an, statt den Start zu verhindern (die Platte bleibt die Wahrheit)", Eingang(b).liste() == [])
    os.unlink(b.pfad("arbeit", "eingang.json"))

    # -- Der Dienst liest nur ein, was im Eingang steht
    muster.stl_binaer(os.path.join(ordner, "D.stl"), 40, 20, 30)
    muster.stl_binaer(os.path.join(ordner, "E.stl"), 41, 20, 30)      # liegt im Ordner, ist aber nicht eingetragen
    os.remove(os.path.join(ordner, "A.stl"))                          # bekannt im Katalog, von aussen gelöscht
    lauf_vorher = s.status["lauf"]
    s.eintragen([os.path.join(ordner, "D.stl")])
    s.warten(120)
    check("Eingetragene Datei wird eingelesen und ist im Katalog", "D" in namen(k))
    check("Der Ordner wird dabei nicht durchsucht: die nicht eingetragene Datei kommt nicht dazu", "E" not in namen(k))
    check("Die Liste ist danach leer", len(s.eingang) == 0)
    check("Ein Teillauf zählt nicht als Lauf des Einlesens (keine neue Nummer, kein neuer Zeitpunkt „zuletzt eingelesen“)",
          s.status["lauf"] == lauf_vorher and s.status["eingang_lauf"] is True)
    check("Ein Teillauf markiert nichts als „fehlt“: der Ort der gelöschten Datei bleibt, bis ein vollständiges Einlesen sie vermisst",
          (w, "A.stl") in k.ort_index())
    check("Die Vorschau der neuen Datei ist danach fertig (Warteschlange der Vorschaubilder läuft im selben Dienst)",
          not k.ausstehende_vorschauen())
    s.lauf()
    check("Das vollständige Einlesen findet die übrigen Dateien und vermisst die gelöschte",
          "E" in namen(k) and (w, "A.stl") not in k.ort_index())

    # -- Anderes als Modelle in Wurzelordnern wird nicht vorgemerkt
    ausserhalb = os.path.join(tmp, "woanders.stl")
    muster.stl_binaer(ausserhalb, 50, 20, 30)
    open(os.path.join(ordner, "notiz.txt"), "w").write("kein Modell")
    check("Eine Datei ausserhalb der Wurzelordner und eine Textdatei kommen nicht in den Eingang",
          s.eintragen([ausserhalb, os.path.join(ordner, "notiz.txt")]) == 0 and len(s.eingang) == 0)

    # -- Eintrag ohne Datei, Kopie mit gleichem Inhalt
    s.eingang.eintragen([(w, "gibtsnicht.stl"), (w, "../ausbruch.stl"), (w, ".versteckt/x.stl")])
    modelle_vorher = len(k.modelle())
    muster.stl_binaer(os.path.join(ordner, "B_Kopie.stl"), 11, 20, 30)     # gleicher Inhalt wie B
    s.eintragen([os.path.join(ordner, "B_Kopie.stl")])
    s.warten(120)
    check("Einträge, deren Datei fehlt, aus dem Ordner herausführen oder versteckt sind: aus der Liste genommen, kein Absturz", len(s.eingang) == 0)
    check("Inhaltsgleiche Kopie: kein zweites Modell, sondern ein Ort dazu (der Hash erkennt sie auch im Teillauf)",
          len(k.modelle()) == modelle_vorher and (w, "B_Kopie.stl") in k.ort_index())

    # -- Abbruch: der Eingang bleibt stehen und der Dienst nimmt ihn nicht von selbst wieder auf
    muster.stl_binaer(os.path.join(ordner, "F.stl"), 60, 20, 30)
    abgebrochen = []

    def beim_hashen(st):
        if st.get("eingang_lauf") and st.get("phase") == "hashen" and not abgebrochen:
            abgebrochen.append(1)
            s.abbrechen()

    s.melden = beim_hashen
    s.eintragen([os.path.join(ordner, "F.stl")])
    s.warten(120)
    s.melden = lambda st: None
    check("Abbruch im Teillauf: die Datei bleibt im Eingang, nichts ist angelegt", len(s.eingang) == 1 and "F" not in namen(k))
    check("… und der Dienst ruht, bis etwas Neues kommt (er nimmt den Eingang nicht von selbst wieder auf)",
          s._aktiv is False and s.status["abgebrochen"] is True)
    s.anstossen()
    s.warten(120)
    check("Neu angestossen: die liegengebliebene Datei wird eingelesen", "F" in namen(k) and len(s.eingang) == 0)

    # -- Vorrang: die Vorschaubilder weichen dem Eingang
    stoff = []
    for i in range(10):
        p = os.path.join(ordner, f"V{i}.stl")
        muster.stl_binaer(p, 70 + i, 20, 30)
        stoff.append(p)
    spaeter = os.path.join(ordner, "Spaeter.stl")
    muster.stl_binaer(spaeter, 99, 20, 30)
    probe = {}

    def beim_vorschau(st):
        if st.get("phase") == "vorschau" and st.get("vorschauen_gesamt") and "nachgelegt" not in probe:
            probe["nachgelegt"] = True
            s.eintragen([spaeter])
        elif probe.get("nachgelegt") and st.get("eingang_lauf") and st.get("phase") == "hashen" and "offen" not in probe:
            probe["offen"] = len(k.ausstehende_vorschauen())       # was im Augenblick, in dem die neue Datei drankommt, noch auf sein Bild wartet

    scan.WEICHEN_STUECK = 2
    s.melden = beim_vorschau
    s.eintragen(stoff)
    s.warten(180)
    s.melden = lambda st: None
    check("Eine Datei, die während der Vorschauen abgelegt wird, kommt dran, bevor die Warteschlange der Bilder leer ist",
          probe.get("offen", 0) > 0 and "Spaeter" in namen(k))
    check("Nichts geht dabei verloren: am Ende sind alle Vorschauen da und der Eingang ist leer",
          not k.ausstehende_vorschauen() and len(s.eingang) == 0 and {f"V{i}" for i in range(10)} <= namen(k))
    b.schliessen()

    # -- Über die Schnittstelle: Hochladen trägt nur ein; der Browser muss nichts anstossen
    api_ordner = os.path.join(tmp, "api_teile")
    os.makedirs(api_ordner)
    muster.stl_binaer(os.path.join(api_ordner, "Alt.stl"), 12, 20, 30)
    bestand_pfad = os.path.join(tmp, "bestand_api")

    def stl_bytes(x):
        p = os.path.join(tempfile.mkdtemp(), "x.stl")
        muster.stl_binaer(p, x, 8, 9)
        return open(p, "rb").read()

    with TestClient(erstelle_app(bestand_pfad, prozesse=2)) as c:
        z = c.app.state.zustand
        c.post("/api/wurzeln", json={"pfad": api_ordner})
        z["scanner"].warten(120)
        wid = c.get("/api/wurzeln").json()[0]["id"]
        lauf_vorher = c.get("/api/stand").json()["scan"]["lauf"]
        r1 = c.post("/api/hochladen", params={"ordner": wid, "name": "Hoch_1.stl"}, content=stl_bytes(31))
        r2 = c.post("/api/hochladen", params={"ordner": wid, "name": "Hoch_2.stl"}, content=stl_bytes(32))
        # Hier bricht „der Browser“ ab: es kommt kein dritter Aufruf, kein Anstossen, nichts.
        z["scanner"].warten(120)
        stand = c.get("/api/stand").json()
        gefunden = {m["name"] for m in c.get("/api/modelle").json()}
        check("Hochladen antwortet ohne Lauf und ohne zu warten", r1.status_code == 200 and r2.status_code == 200 and "lauf" not in r1.json())
        check("Hochgeladene Dateien sind eingelesen, obwohl der Browser nach dem Hochladen nichts mehr tut",
              {"Hoch_1", "Hoch_2"} <= gefunden and stand["eingang"] == 0)
        check("… ohne dass ein vollständiges Einlesen lief", stand["scan"]["lauf"] == lauf_vorher)
    # Neustart mit gefüllter Liste: der Dienst setzt fort, ohne „Beim Start einlesen“ und ohne die Ordner zu durchsuchen
    muster.stl_binaer(os.path.join(api_ordner, "Vorgemerkt.stl"), 33, 20, 30)
    muster.stl_binaer(os.path.join(api_ordner, "Nicht_vorgemerkt.stl"), 34, 20, 30)
    with open(os.path.join(bestand_pfad, "arbeit", "eingang.json"), "w") as f:
        json.dump({"form": 1, "eintraege": [{"wurzel": wid, "pfad": "Vorgemerkt.stl"}]}, f)
    with TestClient(erstelle_app(bestand_pfad, prozesse=2)) as c:
        c.app.state.zustand["scanner"].warten(120)
        gefunden = {m["name"] for m in c.get("/api/modelle").json()}
        check("Neustart mit gefüllter Liste: die vorgemerkte Datei wird eingelesen", "Vorgemerkt" in gefunden)
        check("… die Ordner werden dabei nicht durchsucht, die nicht vorgemerkte Datei bleibt aussen vor",
              "Nicht_vorgemerkt" not in gefunden and c.get("/api/stand").json()["eingang"] == 0)
    muster.ende()
