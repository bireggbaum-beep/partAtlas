"""Hinweis „Kein Verbrauch angegeben“: nur ein 3MF ohne Slicer-Daten (und ohne Referenzdruck mit Gewicht) meldet `verbrauch_fehlt`;
ein geslictes 3MF und Dateien, die gar keine Slicer-Daten tragen können (STL), nicht."""
import os
import tempfile

import muster
from muster import check
from fastapi.testclient import TestClient
from partatlas.main import erstelle_app

if __name__ == "__main__":
    tmp = tempfile.mkdtemp()
    samm = os.path.join(tmp, "3D")
    os.makedirs(samm)
    muster.dreimf(os.path.join(samm, "Roh.3mf"), slice_info=False)
    muster.dreimf(os.path.join(samm, "Geslict.3mf"))
    muster.stl_binaer(os.path.join(samm, "Arm.stl"))
    with TestClient(erstelle_app(os.path.join(tmp, "bestand"), prozesse=2)) as c:
        z = c.app.state.zustand
        c.post("/api/wurzeln", json={"pfad": samm})
        z["scanner"].warten(120)
        z["scanner"].worker.warten(120)
        ms = {m["name"]: c.get(f"/api/modelle/{m['id']}").json() for m in c.get("/api/modelle").json()}
        check("Geslictes 3MF hat Gewicht, kein Hinweis", ms["Geslict"]["gewicht_g"] and ms["Geslict"]["verbrauch_fehlt"] is False)
        check("3MF ohne Slicer-Daten: Hinweis", not ms["Roh"]["gewicht_g"] and ms["Roh"]["verbrauch_fehlt"] is True)
        check("STL: kein Hinweis (sie kann keine Slicer-Daten tragen)", ms["Arm"]["verbrauch_fehlt"] is False)
        did = c.post("/api/drucke", json={"modelle": [ms["Roh"]["id"]], "felder": {"gewicht_g": 12.5, "ergebnis": "gut"}}).json()["id"]
        c.post(f"/api/drucke/{did}/referenz", json={"modell": ms["Roh"]["id"]})
        roh = c.get(f"/api/modelle/{ms['Roh']['id']}").json()
        check("Referenzdruck mit Gewicht: Gewicht kommt vom Druck, kein Hinweis",
              roh["gewicht_g"] == 12.5 and roh["verbrauch_fehlt"] is False)
    muster.ende()
