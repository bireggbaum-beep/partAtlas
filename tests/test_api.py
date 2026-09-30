"""Die Schnittstelle, wie die Oberfläche sie benutzt — und die Wache davor."""
import os
import tempfile

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

        # -- Wache
        fremd = c.post(f"/api/modelle/{zahnrad['id']}/loeschen", headers={"Origin": "http://boese.example"})
        check("Wache: Löschen von fremder Seite abgelehnt (403)", fremd.status_code == 403)
        fremd = c.post(f"/api/modelle/{zahnrad['id']}/loeschen", headers={"Sec-Fetch-Site": "cross-site"})
        check("Wache: Sec-Fetch-Site cross-site abgelehnt", fremd.status_code == 403)
        check("… und das Modell ist noch da", c.get(f"/api/modelle/{zahnrad['id']}").json()["papierkorb"] is False)

        r = c.post(f"/api/modelle/{zahnrad['id']}/slicer", json={"pfad": "/bin/sh"})
        check("Slicer: nur bekannte Programme, kein beliebiger Pfad", r.status_code == 400)

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
