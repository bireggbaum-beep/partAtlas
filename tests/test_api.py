"""Die Schnittstelle, wie die Oberfläche sie benutzt — und die Wache davor."""
import os
import stat
import tempfile
import time

import muster
from muster import check
from fastapi.testclient import TestClient
from partatlas.main import erstelle_app

if __name__ == "__main__":
    tmp = tempfile.mkdtemp()
    sammlung = os.path.join(tmp, "3D-Druck")
    os.makedirs(os.path.join(sammlung, "Technik"))
    muster.dreimf(os.path.join(sammlung, "Technik", "Zahnrad.3mf"))
    muster.stl_binaer(os.path.join(sammlung, "Haken.stl"))

    # Attrappen statt echter Programme: sie schreiben nur auf, womit sie
    # gestartet wurden. Vorne im PATH, damit die Erkennung sie findet.
    attrappen, protokoll = os.path.join(tmp, "bin"), os.path.join(tmp, "gestartet.txt")
    os.makedirs(attrappen)
    for name in ("freecad", "prusa-slicer", "xdg-open", "meincad", "dbus-send"):
        with open(os.path.join(attrappen, name), "w") as f:
            f.write(f'#!/bin/sh\necho "{name} $*" >> "{protokoll}"\n')
        os.chmod(os.path.join(attrappen, name), 0o755)
    os.environ["PATH"] = attrappen + os.pathsep + os.environ["PATH"]

    def gestartet(erwartet):
        for _ in range(50):
            if os.path.exists(protokoll) and erwartet in open(protokoll).read():
                return True
            time.sleep(0.1)
        return False

    with TestClient(erstelle_app(os.path.join(tmp, "bestand"), prozesse=2)) as c:
        z = c.app.state.zustand
        r = c.post("/api/wurzeln", json={"pfad": sammlung})
        check("Ordner hinzufügen startet das Einlesen", r.status_code == 200)
        z["scanner"].warten(120)
        check("Wurzel falsch: verständliche Meldung statt Absturz",
              c.post("/api/wurzeln", json={"pfad": "/gibt/es/nicht"}).json().get("fehler", "").startswith("Kein Ordner"))

        liste = c.get("/api/modelle").json()
        check("Liste liefert beide Modelle mit Kachel-Feldern",
              sorted(m["name"] for m in liste) == ["Haken", "Zahnrad"] and all("vorschau" in m for m in liste))
        zahnrad = next(m for m in liste if m["name"] == "Zahnrad")
        check("Suche", [m["name"] for m in c.get("/api/modelle", params={"q": "zahn"}).json()] == ["Zahnrad"])
        check("Filter nach Format", [m["name"] for m in c.get("/api/modelle", params={"format": "stl"}).json()] == ["Haken"])

        r = c.get(f"/api/vorschau/{zahnrad['hash']}.png")
        check("Vorschaubild ausgeliefert, lange cachebar", r.status_code == 200
              and r.headers["content-type"] == "image/png" and "immutable" in r.headers["cache-control"])
        check("Vorschau: nur echte Hashes, kein Pfad durch die Hintertür",
              c.get("/api/vorschau/..%2F..%2Fetc%2Fpasswd.png").status_code == 404)

        c.post(f"/api/modelle/{zahnrad['id']}/tags", json={"tag": "#Funktional"})
        m = c.get(f"/api/modelle/{zahnrad['id']}").json()
        check("Tag hinzufügen: ohne #, klein geschrieben", "funktional" in m["tags"])
        check("Tag-Liste zählt über die Nachbarschaft",
              {t["name"]: t["anzahl"] for t in c.get("/api/tags").json()}.get("funktional") == 1)
        c.delete(f"/api/modelle/{zahnrad['id']}/tags/funktional")
        check("Tag entfernen", "funktional" not in c.get(f"/api/modelle/{zahnrad['id']}").json()["tags"])

        r = c.patch(f"/api/modelle/{zahnrad['id']}", json={"favorit": True, "gedruckt": True})
        check("Favorit und Gedruckt setzen", r.json()["favorit"] and r.json()["gedruckt"])
        check("Unbekanntes Feld wird abgelehnt", c.patch(f"/api/modelle/{zahnrad['id']}", json={"hash": "x"}).status_code == 400)

        # -- Ordner wählen: durchsuchen statt Pfad tippen
        os.makedirs(os.path.join(tmp, ".versteckt"))
        d = c.get("/api/durchsuchen", params={"pfad": tmp}).json()
        check("Durchsuchen: Unterordner sichtbar, versteckte nicht, Eltern-Ordner bekannt",
              "3D-Druck" in [o["name"] for o in d["ordner"]] and ".versteckt" not in [o["name"] for o in d["ordner"]]
              and d["eltern"] == os.path.dirname(tmp))
        d = c.get("/api/durchsuchen", params={"pfad": sammlung}).json()
        check("… zählt die Modelldateien samt Unterordnern, bevor man wählt", d["modelle"] == 2 and d["vollstaendig"])
        check("… mit dem persönlichen Ordner als Sprungziel",
              d["sprungziele"][0]["pfad"] == os.path.expanduser("~"))
        check("Kein Ordner: verständliche Meldung",
              c.get("/api/durchsuchen", params={"pfad": "/gibt/es/nicht"}).json().get("fehler", "").startswith("Kein Ordner"))

        # -- Wache
        fremd = c.post(f"/api/modelle/{zahnrad['id']}/loeschen", headers={"Origin": "http://boese.example"})
        check("Wache: Löschen von fremder Seite abgelehnt (403)", fremd.status_code == 403)
        fremd = c.post(f"/api/modelle/{zahnrad['id']}/loeschen", headers={"Sec-Fetch-Site": "cross-site"})
        check("Wache: Sec-Fetch-Site cross-site abgelehnt", fremd.status_code == 403)
        check("… und das Modell ist noch da", c.get(f"/api/modelle/{zahnrad['id']}").json()["papierkorb"] is False)

        # -- Öffnen in …
        prog = c.get("/api/programme").json()
        art = {p["name"]: p["art"] for p in prog["programme"]}
        check("Erkennung: FreeCAD als CAD, PrusaSlicer als Slicer", art.get("FreeCAD") == "cad" and art.get("PrusaSlicer") == "slicer")
        fc = next(p["pfad"] for p in prog["programme"] if p["name"] == "FreeCAD")
        check("Standard ohne Einstellung: STEP ins CAD, 3MF und STL in den Slicer",
              prog["standard"]["step"] == fc and "prusa-slicer" in prog["standard"]["3mf"] and "prusa-slicer" in prog["standard"]["stl"])
        haken = next(m for m in liste if m["name"] == "Haken")
        r = c.post(f"/api/modelle/{zahnrad['id']}/oeffnen", json={})
        check("Hauptknopf: Standardprogramm bekommt die Datei des Modells",
              r.json().get("programm") == "PrusaSlicer" and gestartet("prusa-slicer " + os.path.join(sammlung, "Technik", "Zahnrad.3mf")))
        c.post(f"/api/modelle/{haken['id']}/oeffnen", json={"pfad": fc})
        check("Öffnen mit: gewähltes Programm", gestartet("freecad " + os.path.join(sammlung, "Haken.stl")))
        c.post(f"/api/modelle/{haken['id']}/oeffnen", json={"system": True})
        check("Mit dem System öffnen: xdg-open", gestartet("xdg-open " + os.path.join(sammlung, "Haken.stl")))
        c.post(f"/api/modelle/{haken['id']}/im_ordner")
        check("Im Ordner zeigen: Dateimanager über ShowItems mit der Datei markiert (file://-Adresse)",
              gestartet("dbus-send --session") and "ShowItems array:string:file://" + os.path.join(sammlung, "Haken.stl") in open(protokoll).read())
        r = c.post(f"/api/modelle/{zahnrad['id']}/oeffnen", json={"pfad": "/bin/sh"})
        check("Öffnen: nur bekannte Programme, kein beliebiger Pfad", r.status_code == 400)
        r = c.put("/api/einstellungen", json={"programme": [{"name": "Kaputt", "pfad": os.path.join(tmp, "gibtsnicht")}]})
        check("Eigenes Programm: nur was es gibt und ausführbar ist", r.status_code == 400)
        mein = os.path.join(attrappen, "meincad")
        c.put("/api/einstellungen", json={"programme": [{"name": "Mein CAD", "pfad": mein, "art": "cad"}],
                                           "standard_programm": {"stl": mein}})
        c.post(f"/api/modelle/{haken['id']}/oeffnen", json={})
        check("Eigenes Programm als Standard für STL übernimmt den Hauptknopf", gestartet("meincad " + os.path.join(sammlung, "Haken.stl")))

        # -- Löschen über die API
        v = c.get(f"/api/modelle/{zahnrad['id']}/loeschen").json()
        check("Löschvorschau über die API", len(v["dateien"]) == 1 and len(v["knoten"]) == 1)
        c.post(f"/api/modelle/{zahnrad['id']}/loeschen", headers={"Sec-Fetch-Site": "same-origin"})
        check("Gelöscht: Datei weg aus dem Ordner", not os.path.exists(os.path.join(sammlung, "Technik", "Zahnrad.3mf")))
        check("Zähler: Papierkorb 1", c.get("/api/zaehler").json()["papierkorb"] == 1)
        c.post(f"/api/modelle/{zahnrad['id']}/wiederherstellen")
        check("Wiederhergestellt: Datei zurück", os.path.exists(os.path.join(sammlung, "Technik", "Zahnrad.3mf")))

        baum = c.get("/api/ordner").json()
        check("Ordnerbaum über die API", baum[0]["name"] == "3D-Druck" and baum[0]["kinder"][0]["name"] == "Technik")
        check("Oberfläche wird ausgeliefert", "partAtlas" in c.get("/").text)
    muster.ende()
